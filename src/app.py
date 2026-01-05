import streamlit as st
import pandas as pd
import os
import sys
import tkinter as tk
from tkinter import filedialog
import shutil

# Perform path magic to ensure imports work when running from command line
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.application.interfaces import AnalysisProgressCallback
from src.infrastructure.repositories import FileProjectRepository
from src.infrastructure.llm_gateway import LLMGatewayImpl
from src.infrastructure.file_converter import FileConverter
from src.application.use_cases import (
    ManageProjectUseCase,
    VerifyRequirementsUseCase,
    BreakdownUseCase,
)
from src.application.services.breakdown_service import BreakdownService
from src.interface_adapters.controllers import StreamlitController
from src.interface_adapters.presenters import ResultPresenter

# --- Page Config ---
st.set_page_config(layout="wide", page_title="Requirements Verification AI")


# --- Dependency Injection ---
@st.cache_resource
def get_controller():
    repo = FileProjectRepository(root_dir=os.getcwd())
    llm = LLMGatewayImpl()
    file_provider = FileConverter()

    manage_uc = ManageProjectUseCase(repo)
    verify_uc = VerifyRequirementsUseCase(repo, llm, file_provider)

    breakdown_service = BreakdownService(llm)
    breakdown_uc = BreakdownUseCase(breakdown_service)

    return StreamlitController(manage_uc, verify_uc, breakdown_uc)


controller = get_controller()
presenter = ResultPresenter()


# --- Callbacks ---
class UIProgressCallback(AnalysisProgressCallback):
    def __init__(self, log_container):
        self.log_container = log_container
        self.logs = []

    def on_progress(self, step: str, percentage: int):
        pass

    def on_log(self, message: str):
        self.logs.append(message)
        self.log_container.text_area(
            "Execution Logs", value="\n".join(self.logs), height=300
        )


# --- Helper Functions ---
def ensure_project_structure(project_id):
    """Ensure standard directories exist."""
    base = os.path.join("projects", str(project_id))
    os.makedirs(os.path.join(base, "uploads"), exist_ok=True)
    os.makedirs(os.path.join(base, "requirements"), exist_ok=True)
    os.makedirs(os.path.join(base, "reports"), exist_ok=True)


def get_project_files_grouped(project_id):
    """Return files grouped by category."""
    ensure_project_structure(project_id)
    base = os.path.join("projects", str(project_id))

    structure = {"uploads": [], "requirements": [], "reports": []}

    for category in structure.keys():
        dir_path = os.path.join(base, category)
        if os.path.exists(dir_path):
            for f in os.listdir(dir_path):
                if not f.startswith("."):
                    structure[category].append(os.path.join(category, f))

    return structure


def select_folder():
    try:
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", 1)
        folder_path = filedialog.askdirectory()
        root.destroy()
        return folder_path
    except Exception:
        return None


# --- Main Layout ---

# Initialize Session State
if "selected_project_id" not in st.session_state:
    st.session_state["selected_project_id"] = None
if "selected_file" not in st.session_state:
    st.session_state["selected_file"] = None
if "logs" not in st.session_state:
    st.session_state["logs"] = []
if "breakdown_session" not in st.session_state:
    st.session_state["breakdown_session"] = None
if "breakdown_messages" not in st.session_state:
    st.session_state["breakdown_messages"] = []


# Logic to handle Project Switching
def on_project_change():
    st.session_state["selected_file"] = None
    st.session_state["logs"] = []
    st.session_state["breakdown_session"] = None
    st.session_state["breakdown_messages"] = []


# --- Left Sidebar: Project & Files ---
with st.sidebar:
    st.header("Explorer")

    # 1. Project Section
    st.subheader("Project")
    projects = controller.get_all_projects()
    project_options = {p.name: p.id for p in projects}

    # Project Dropdown
    project_names = ["Select..."] + list(project_options.keys()) + ["Create New..."]

    current_index = 0
    if st.session_state["selected_project_id"]:
        current_name = next(
            (
                name
                for name, pid in project_options.items()
                if pid == st.session_state["selected_project_id"]
            ),
            None,
        )
        if current_name in project_names:
            current_index = project_names.index(current_name)

    selected_project_name = st.selectbox(
        "Select Project",
        project_names,
        index=current_index,
        key="project_selector",
        on_change=on_project_change,
    )

    # Handle Selection
    if selected_project_name == "Create New...":
        with st.expander("Create New Project", expanded=True):
            new_name = st.text_input("Name")
            new_path_val = st.text_input("Path", value=os.getcwd())
            if st.button("Browse..."):
                selected = select_folder()
                if selected:
                    st.info(f"Selected: {selected}")

            if st.button("Create"):
                if new_name and new_path_val:
                    p = controller.create_project(new_name, new_path_val)
                    ensure_project_structure(p.id)
                    st.success(f"Created {p.name}")
                    st.rerun()

    elif selected_project_name != "Select...":
        st.session_state["selected_project_id"] = project_options[selected_project_name]
        ensure_project_structure(st.session_state["selected_project_id"])
    else:
        st.session_state["selected_project_id"] = None

    # Project Actions
    if st.session_state["selected_project_id"]:
        pass  # Could add delete here

    st.divider()

    # 2. Files Section
    st.subheader("Files")
    if st.session_state["selected_project_id"]:
        project_id = st.session_state["selected_project_id"]

        # File Uploader -> uploads/
        uploaded_file = st.file_uploader(
            "Upload to /uploads", label_visibility="collapsed"
        )
        if uploaded_file:
            uploads_dir = os.path.join("projects", str(project_id), "uploads")
            file_path = os.path.join(uploads_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            controller.add_file(project_id, file_path)
            st.toast(f"Uploaded {uploaded_file.name}")
            st.rerun()

        # Create New File -> requirements/ (Manual creation)
        with st.expander("New Requirement Doc"):
            new_req_name = st.text_input("Filename", placeholder="spec.md")
            if st.button("Create"):
                if new_req_name:
                    req_dir = os.path.join("projects", str(project_id), "requirements")
                    file_path = os.path.join(req_dir, new_req_name)
                    if not os.path.exists(file_path):
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write("# System Requirements\n")
                        # We might not need to register with 'add_file' if we just scan,
                        # but keeping it consistent with existing logic:
                        controller.add_file(project_id, file_path)
                        st.toast(f"Created {new_req_name}")
                        st.rerun()
                    else:
                        st.error("File exists")

        # File Tree
        grouped_files = get_project_files_grouped(project_id)

        # Flatten for the radio functionality, but maybe use headers to separate visualy?
        # Streamlit radio is flat. We can prefix.

        flat_files = []
        for cat, flist in grouped_files.items():
            for f in flist:
                flat_files.append(f)  # e.g. "uploads/notes.txt"

        if flat_files:
            # Check if selection is still valid
            if (
                st.session_state["selected_file"]
                and st.session_state["selected_file"] not in flat_files
            ):
                st.session_state["selected_file"] = None

            curr_idx = 0
            if st.session_state["selected_file"] in flat_files:
                curr_idx = flat_files.index(st.session_state["selected_file"])

            selected_str = st.radio(
                "Files", flat_files, index=curr_idx, label_visibility="collapsed"
            )

            # Detect change to clear logs or reset editor key
            if selected_str != st.session_state["selected_file"]:
                st.session_state["selected_file"] = selected_str
                # Force reload of editor content by clearing it?
                # We handle this in the Editor section by checking file path
                st.rerun()
        else:
            st.info("No files.")

    else:
        st.caption("Select project.")


if "app_mode" not in st.session_state:
    st.session_state["app_mode"] = "Review"

# --- Main Area & Right Sidebar ---
col_editor, col_right = st.columns([3, 1])

# --- Center: Editor ---
with col_editor:
    st.subheader("Editor")

    current_file_path = None
    file_content = ""

    if st.session_state["selected_project_id"] and st.session_state["selected_file"]:
        project_id = st.session_state["selected_project_id"]
        rel_path = st.session_state["selected_file"]
        abs_path = os.path.join(os.getcwd(), "projects", str(project_id), rel_path)
        current_file_path = abs_path

        if os.path.exists(abs_path):
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                file_content = f.read()
        else:
            st.error(f"File not found: {rel_path}")

    # Use a dynamic key based on filename to ensure fresh Text Area
    editor_key = f"editor_{st.session_state['selected_project_id']}_{st.session_state['selected_file']}"

    # If the file is not selected, show info
    if not current_file_path:
        st.info("Select a file to edit.")
    else:
        # Tabs for Edit / Preview
        tab_edit, tab_preview = st.tabs(["Edit", "Preview"])

        with tab_edit:
            new_content = st.text_area(
                f"Content: {st.session_state['selected_file']}",
                value=file_content,
                height=600,
                key=editor_key,
            )

            if st.button("Save Changes"):
                with open(current_file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                st.toast(f"Saved {st.session_state['selected_file']}")

        with tab_preview:
            # If changed, show new_content (from state, but st.text_area updates state on rerun)
            # Actually strictly 'new_content' contains the latest from text_area widget in this run
            st.markdown(new_content)

# --- Right Sidebar: Actions & Logs / Breakdown ---
with col_right:
    # Use key='app_mode' to persist state across reruns (fixes reset issue)
    mode = st.radio("Mode", ["Review", "Breakdown"], horizontal=True, key="app_mode")
    st.divider()

    if mode == "Review":
        st.subheader("Review / Verification")

        # Check if current file is in 'requirements/'?
        # User requested to review content.

        if current_file_path:
            st.text(f"Target: {os.path.basename(current_file_path)}")

            if st.button(
                "Start Verification", type="primary", use_container_width=True
            ):
                # Save current content first?
                # Assuming user saved.

                progress_container = st.empty()
                log_container = st.empty()
                callback = UIProgressCallback(log_container)

                with st.spinner("Verifying..."):
                    try:
                        # We use the Controller logic, but verify ONLY the current file?
                        # Or the whole project? Original logic verifies ALL files in project.input_files
                        # User constraint: "review the requirement document"
                        # We should probably respect the 'input_files' list effectively.
                        # For now, let's Stick to Project Verification as per UseCase
                        # But we should make sure the current file is part of it.

                        # Add current file to project if not there?
                        # The controller.add_file is explicit. The file explorer just looks at disk.
                        # Let's ensure consistency:
                        controller.add_file(
                            st.session_state["selected_project_id"], current_file_path
                        )

                        result = controller.run_verification(
                            st.session_state["selected_project_id"], callback
                        )
                        st.success("Complete!")

                        # Save Report to reports/
                        project_root = os.path.join(
                            "projects", str(st.session_state["selected_project_id"])
                        )
                        report_path = os.path.join(
                            project_root, "reports", "latest_report.md"
                        )
                        with open(report_path, "w", encoding="utf-8") as f:
                            f.write(result.raw_report)

                        st.toast("Report Saved")
                        # Force open report?
                        # It's in reports/latest_report.md
                        st.rerun()

                    except Exception as e:
                        st.error(f"Error: {e}")
        else:
            st.info("Open a requirement file to review.")

        # Logs
        if st.session_state.get("logs"):
            st.text_area(
                "Logs",
                value="\n".join(st.session_state["logs"]),
                height=200,
                disabled=True,
            )

    elif mode == "Breakdown":
        st.subheader("Breakdown Generator")

        # 1. Select Input File (from uploads)
        if st.session_state["selected_project_id"]:
            files_map = get_project_files_grouped(
                st.session_state["selected_project_id"]
            )
            uploads = files_map["uploads"]

            if not uploads:
                st.warning("No files in 'uploads/'. Please upload meeting notes first.")
            else:
                input_file_rel = st.selectbox("Source (Meeting Notes)", uploads)

                output_name = st.text_input(
                    "Output Filename", value="requirements/draft_spec.md"
                )

                # Check for active session
                session = st.session_state["breakdown_session"]

                if st.button(
                    "Generate Draft & Start Chat",
                    type="primary",
                    use_container_width=True,
                ):
                    # Read Input
                    p_id = st.session_state["selected_project_id"]
                    abs_input = os.path.join("projects", str(p_id), input_file_rel)

                    if not os.path.exists(abs_input):
                        st.error(f"Input file not found: {abs_input}")
                    else:
                        with open(abs_input, "r", encoding="utf-8") as f:
                            input_text = f.read()

                        with st.spinner("Analyzing & Generating Draft..."):
                            try:
                                session_data = controller.breakdown_uc.start_session(
                                    input_text
                                )
                                st.session_state["breakdown_session"] = session_data
                                st.session_state["breakdown_messages"] = [
                                    {
                                        "role": "assistant",
                                        "content": "I have created the draft. Please check the editor. I also have some questions.",
                                    }
                                ]

                                # Save Draft to Output
                                abs_output = os.path.join(
                                    "projects", str(p_id), output_name
                                )
                                with open(abs_output, "w", encoding="utf-8") as f:
                                    f.write(session_data.requirements)

                                # Switch Editor to this new file
                                st.session_state["selected_file"] = output_name
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error during breakdown: {e}")
                                # Print strict traceback
                                import traceback

                                st.text(traceback.format_exc())

        # Chat Interface
        if st.session_state.get("breakdown_session"):
            st.divider()
            st.caption("Chat")

            # Chat History
            chat_container = st.container(height=300)
            with chat_container:
                for msg in st.session_state["breakdown_messages"]:
                    st.chat_message(msg["role"]).write(msg["content"])

                # Current Question
                session = st.session_state["breakdown_session"]
                if session.questions:
                    q = session.questions[0]
                    st.info(f"**Question**:\n{q.question}")
                else:
                    st.success("Drafting complete.")

            # Input
            if prompt := st.chat_input("Answer..."):
                st.session_state["breakdown_messages"].append(
                    {"role": "user", "content": prompt}
                )

                session = st.session_state["breakdown_session"]
                if session.questions:
                    q = session.questions[0]
                    is_valid, follow_up = controller.breakdown_uc.answer_question(
                        session, q.id, prompt
                    )

                    if is_valid:
                        st.session_state["breakdown_messages"].append(
                            {"role": "assistant", "content": "Updating requirements..."}
                        )
                        # Update File
                        new_reqs = controller.breakdown_uc.update_requirements(session)
                        session.requirements = new_reqs

                        # Write to current open file (Output file)
                        # We assume the user is still on the output file or we overwrite the one we created
                        # Better: Write to the file associated with 'selected_file' if it matches?
                        # Or just the originally specified output?
                        # Let's overwrite currently open file IF it is in requirements/
                        if current_file_path:
                            with open(current_file_path, "w", encoding="utf-8") as f:
                                f.write(new_reqs)

                        # Next Q logic (simplified)
                        if not session.questions:
                            new_qs = controller.breakdown_uc.generate_questions(session)
                            if new_qs:
                                session.questions.extend(new_qs)

                        st.rerun()
                    else:
                        st.session_state["breakdown_messages"].append(
                            {"role": "assistant", "content": f"Clarify: {follow_up}"}
                        )
                        st.rerun()

            if st.button("End Session", type="secondary"):
                st.session_state["breakdown_session"] = None
                st.session_state["breakdown_messages"] = []
                st.rerun()
