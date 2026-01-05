import streamlit as st
import pandas as pd
import os
import sys

# Perform path magic to ensure imports work when running from command line
# Add the project root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.application.interfaces import AnalysisProgressCallback
from src.infrastructure.repositories import FileProjectRepository
from src.infrastructure.llm_gateway import LLMGatewayImpl
from src.infrastructure.file_converter import FileConverter
from src.application.use_cases import ManageProjectUseCase, VerifyRequirementsUseCase
from src.interface_adapters.controllers import StreamlitController
from src.interface_adapters.presenters import ResultPresenter

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
    def __init__(self, progress_bar, status_text):
        self.progress_bar = progress_bar
        self.status_text = status_text
        self.logs = []

    def on_progress(self, step: str, percentage: int):
        self.progress_bar.progress(percentage)
        self.status_text.text(step)

    def on_log(self, message: str):
        self.logs.append(message)


# --- Sidebar ---
st.sidebar.title("Project Management")

# Project Selection
projects = controller.get_all_projects()
project_options = {p.name: p.id for p in projects}

# Add "Create New" option
project_names = (
    ["Select a project..."] + list(project_options.keys()) + ["Create New..."]
)
selected_project_name = st.sidebar.selectbox("Current Project", project_names, index=0)

current_project_id = None
if selected_project_name in project_options:
    current_project_id = project_options[selected_project_name]

# Helper for directory picker
import tkinter as tk
from tkinter import filedialog


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


if selected_project_name == "Create New...":
    st.sidebar.subheader("New Project Details")
    new_name = st.sidebar.text_input("Project Name")

    # Directory selection
    if "new_project_path" not in st.session_state:
        st.session_state["new_project_path"] = os.getcwd()

    new_path = st.sidebar.text_input(
        "Directory Path", value=st.session_state.get("new_project_path", os.getcwd())
    )

    # Wide layout for Browse button below input
    if st.sidebar.button("Browse...", use_container_width=True):
        selected = select_folder()
        if selected:
            st.session_state["new_project_path"] = selected
            st.rerun()

    if st.sidebar.button("Create Project", type="primary", use_container_width=True):
        if new_name and new_path:
            p = controller.create_project(new_name, new_path)
            st.sidebar.success(f"Created {p.name}")
            # Clear state
            if "new_project_path" in st.session_state:
                del st.session_state["new_project_path"]
            st.rerun()

# File Management & Settings
if current_project_id:
    st.sidebar.markdown("---")
    st.sidebar.subheader("Files")

    # Retrieve project data
    current_project = next((p for p in projects if p.id == current_project_id), None)

    if current_project:
        for f in current_project.input_files:
            st.sidebar.text(os.path.basename(f))

        uploaded_file = st.sidebar.file_uploader(
            "Add File", type=["md", "txt", "pdf", "docx", "xlsx"]
        )
        if uploaded_file:
            uploads_dir = os.path.join("projects", str(current_project_id), "uploads")
            os.makedirs(uploads_dir, exist_ok=True)
            file_path = os.path.join(uploads_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            controller.add_file(current_project_id, file_path)
            st.sidebar.success(f"Added {uploaded_file.name}")
            st.rerun()

    # Project Settings (Deletion)
    st.sidebar.markdown("---")
    with st.sidebar.expander("Settings"):
        if st.button("Delete Project", type="secondary"):
            controller.delete_project(current_project_id)
            st.sidebar.success("Project deleted.")
            # Reset selection
            st.rerun()

# --- Main Area ---
st.title("Requirements Verification AI")

if not current_project_id:
    st.info("Please select or create a project to begin.")
else:
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Start Verification", type="primary", use_container_width=True):
            progress_bar = st.progress(0)
            status_text = st.empty()

            # Log Container
            log_expander = st.expander("Verification Logs", expanded=True)
            log_container = log_expander.empty()

            # Custom Callback to update logs in real-time
            class RealtimeLogCallback(UIProgressCallback):
                def __init__(self, progress_bar, status_text, log_container):
                    super().__init__(progress_bar, status_text)
                    self.log_container = log_container

                def on_log(self, message: str):
                    super().on_log(message)
                    self.log_container.text("\n".join(self.logs))

            callback = RealtimeLogCallback(progress_bar, status_text, log_container)

            with st.spinner("Verifying..."):
                try:
                    result = controller.run_verification(current_project_id, callback)
                    st.session_state["last_result"] = result
                    st.session_state["logs"] = callback.logs
                    st.success("Verification Complete!")
                except Exception as e:
                    st.error(f"Verification Failed: {e}")
                    import traceback

                    st.error(traceback.format_exc())

    if (
        "last_result" in st.session_state
        and st.session_state["last_result"].project_id == current_project_id
    ):
        result = st.session_state["last_result"]

        # Dashboard Cards
        c1, c2 = st.columns(2)
        c1.metric("Total Defects", len(result.defects))

        # Count by severity
        critical = sum(1 for d in result.defects if d.severity == "Critical")
        c2.metric("Critical Defects", critical)

        tab1, tab2, tab3 = st.tabs(["Report", "Defect List", "Logs"])

        with tab1:
            st.markdown(result.raw_report)

        with tab2:
            if result.defects:
                df = presenter.present_defects(result.defects)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No defects found.")

        with tab3:
            st.text_area(
                "Logs", value="\n".join(st.session_state.get("logs", [])), height=300
            )
