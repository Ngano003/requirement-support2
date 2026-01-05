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
from src.application.use_cases import ManageProjectUseCase, VerifyRequirementsUseCase
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

    return StreamlitController(manage_uc, verify_uc)


controller = get_controller()
presenter = ResultPresenter()


# --- Callbacks ---
class UIProgressCallback(AnalysisProgressCallback):
    def __init__(self, log_container):
        self.log_container = log_container
        self.logs = []

    def on_progress(self, step: str, percentage: int):
        # We might not have a progress bar in the new layout or it might be in the sidebar
        # For now, let's just log the step
        pass

    def on_log(self, message: str):
        self.logs.append(message)
        self.log_container.text_area(
            "Execution Logs", value="\n".join(self.logs), height=300
        )


# --- Helper Functions ---
def get_project_files(project_id):
    """Recursively list files in the project directory."""
    project_path = os.path.join("projects", str(project_id))
    file_list = []

    if not os.path.exists(project_path):
        return []

    for root, dirs, files in os.walk(project_path):
        for file in files:
            # Skip hidden files or specific system files if needed
            if file.startswith("."):
                continue
            # Make path relative to project dir for display
            rel_path = os.path.relpath(os.path.join(root, file), project_path)
            file_list.append(rel_path)

    # Sort files: directories first (not easy with relpath), or just alpha
    return sorted(file_list)


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


# Logic to handle Project Switching
def on_project_change():
    st.session_state["selected_file"] = None
    st.session_state["logs"] = []


# --- Left Sidebar: Project & Files ---
with st.sidebar:
    st.header("Explorer")

    # 1. Project Section
    st.subheader("Project")
    projects = controller.get_all_projects()
    project_options = {p.name: p.id for p in projects}

    # Project Dropdown
    project_names = ["Select..."] + list(project_options.keys()) + ["Create New..."]

    # Find index of current selection
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
                    # simplistic hack: just show it (real implementation needs rerun or session state handling specifically for this input)
                    st.info(f"Selected: {selected}")
                    # In a real app, we'd bind this to session state to update the text input

            if st.button("Create"):
                if new_name and new_path_val:
                    p = controller.create_project(new_name, new_path_val)
                    st.success(f"Created {p.name}")
                    st.rerun()

    elif selected_project_name != "Select...":
        st.session_state["selected_project_id"] = project_options[selected_project_name]
    else:
        st.session_state["selected_project_id"] = None

    # Project Actions (Delete)
    if st.session_state["selected_project_id"]:
        if st.button("Delete Project", type="secondary"):
            controller.delete_project(st.session_state["selected_project_id"])
            st.session_state["selected_project_id"] = None
            st.rerun()

    st.divider()

    # 2. Files Section
    st.subheader("Files")
    if st.session_state["selected_project_id"]:
        # File Uploader
        uploaded_file = st.file_uploader("Upload File", label_visibility="collapsed")
        if uploaded_file:
            # Save uploaded file
            project_id = st.session_state["selected_project_id"]
            uploads_dir = os.path.join("projects", str(project_id), "uploads")
            os.makedirs(uploads_dir, exist_ok=True)
            file_path = os.path.join(uploads_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            controller.add_file(project_id, file_path)
            st.toast(f"Uploaded {uploaded_file.name}")
            st.rerun()

        # Create New File
        with st.expander("Create File", expanded=False):
            new_file_name = st.text_input("New Filename", placeholder="example.md")
            if st.button("Create", key="create_file_btn"):
                if new_file_name:
                    project_id = st.session_state["selected_project_id"]
                    # Default to root of project
                    file_path = os.path.join("projects", str(project_id), new_file_name)
                    if not os.path.exists(file_path):
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write("")  # Empty file
                        controller.add_file(project_id, file_path)
                        st.toast(f"Created {new_file_name}")
                        st.rerun()
                    else:
                        st.error("File already exists.")

        # File Tree/List
        files = get_project_files(st.session_state["selected_project_id"])

        # Display as a radio list (acts as a selector)
        # Using a specialized component (like st_tree) would be better, but standard radio works for simple lists
        if files:
            selected_file = st.radio(
                "Project Files",
                files,
                index=(
                    0
                    if not st.session_state["selected_file"]
                    else (
                        files.index(st.session_state["selected_file"])
                        if st.session_state["selected_file"] in files
                        else 0
                    )
                ),
                label_visibility="collapsed",
            )
            st.session_state["selected_file"] = selected_file
        else:
            st.info("No files found.")
            st.session_state["selected_file"] = None
    else:
        st.caption("Select a project to view files.")


# --- Main Area & Right Sidebar ---
# Layout: Editor (Left/Center) | Actions & Logs (Right)
col_editor, col_right = st.columns([3, 1])

# --- Center: Editor ---
with col_editor:
    st.subheader("Editor")

    current_file_path = None
    if st.session_state["selected_project_id"] and st.session_state["selected_file"]:
        project_id = st.session_state["selected_project_id"]
        rel_path = st.session_state["selected_file"]
        # Construct absolute path
        # Note: In get_project_files we listed relative to projects/{id}
        abs_path = os.path.join(os.getcwd(), "projects", str(project_id), rel_path)

        if os.path.exists(abs_path):
            current_file_path = abs_path
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                file_content = f.read()

            # Editor Text Area
            # Key uses file path to ensure state resets when switching files
            new_content = st.text_area(
                f"File: {rel_path}",
                value=file_content,
                height=600,
                key=f"editor_{rel_path}",
            )

            # Save Button
            if st.button("Save Changes"):
                with open(abs_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                st.toast(f"Saved {rel_path}")
        else:
            st.error(f"File not found: {rel_path}")
    else:
        st.info("Select a file from the sidebar to edit.")

# --- Right Sidebar: Actions & Logs ---
with col_right:
    st.subheader("Actions")

    if st.session_state["selected_project_id"]:
        if st.button("Start Verification", type="primary", use_container_width=True):
            # Run Verification
            progress_container = st.empty()
            log_container = st.empty()

            callback = UIProgressCallback(log_container)

            with st.spinner("Verifying..."):
                try:
                    result = controller.run_verification(
                        st.session_state["selected_project_id"], callback
                    )
                    st.success("Verification Complete!")

                    # Save the report prominently so it appears in the file list
                    # The repository already saves it to reports/timestamp/report.md
                    # Let's copy it to 'verification_report.md' in the project root for easy access
                    project_root = os.path.join(
                        "projects", str(st.session_state["selected_project_id"])
                    )
                    latest_report_path = os.path.join(
                        project_root, "verification_report.md"
                    )

                    with open(latest_report_path, "w", encoding="utf-8") as f:
                        f.write(result.raw_report)

                    # Also save JSON result for good measure
                    latest_json_path = os.path.join(
                        project_root, "verification_result.json"
                    )
                    with open(latest_json_path, "w", encoding="utf-8") as f:
                        f.write(result.model_dump_json(indent=2))

                    st.toast("Report saved to verification_report.md")

                    # Force rerun to update file list
                    st.rerun()

                except Exception as e:
                    st.error(f"Error: {e}")
                    import traceback

                    st.text(traceback.format_exc())
    else:
        st.caption("Select a project to run verification.")

    st.subheader("Logs")
    # Log display area handled by callback or session state
    if st.session_state.get("logs"):
        st.text_area(
            "Log Output",
            value="\n".join(st.session_state["logs"]),
            height=400,
            disabled=True,
        )
    else:
        st.caption("No logs available.")
