import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
import pandas as pd
import os

from src.application.interfaces import AnalysisProgressCallback
from src.infrastructure.repositories import FileProjectRepository
from src.infrastructure.llm_gateway import LLMGatewayImpl
from src.infrastructure.file_converter import FileConverter
from src.domain.services import GraphAnalysisService, SemanticAnalysisService
from src.application.use_cases import ManageProjectUseCase, AnalyzeRequirementsUseCase
from src.interface_adapters.controllers import StreamlitController
from src.interface_adapters.presenters import ResultPresenter
from src.domain.models import ProjectId

st.set_page_config(layout="wide", page_title="Requirements Review AI")


# --- Dependency Injection ---
@st.cache_resource
def get_controller():
    repo = FileProjectRepository(root_dir=os.getcwd())
    llm = LLMGatewayImpl()
    file_provider = FileConverter()
    graph_service = GraphAnalysisService()
    semantic_service = SemanticAnalysisService(llm)

    manage_uc = ManageProjectUseCase(repo)
    analyze_uc = AnalyzeRequirementsUseCase(
        repo, llm, graph_service, semantic_service, file_provider
    )

    return StreamlitController(manage_uc, analyze_uc)


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

if selected_project_name == "Create New...":
    with st.sidebar.form("create_project_form"):
        new_name = st.text_input("Project Name")
        new_path = st.text_input("Directory Path", value=os.getcwd())
        submitted = st.form_submit_button("Create")
        if submitted and new_name and new_path:
            p = controller.create_project(new_name, new_path)
            st.sidebar.success(f"Created {p.name}")
            st.rerun()

# File Management
if current_project_id:
    st.sidebar.markdown("---")
    st.sidebar.subheader("Files")

    # Retrieve project data to show files (need to fetch project object)
    # Controller doesn't expose get_project directly in interface but we can use list_projects or add method
    # For now, simplistic approach: re-fetch via list loop or add get_project to controller if needed.
    # Actually list_projects returns Project objects.
    current_project = next((p for p in projects if p.id == current_project_id), None)

    if current_project:
        for f in current_project.input_files:
            st.sidebar.text(os.path.basename(f))

        uploaded_file = st.sidebar.file_uploader(
            "Add File", type=["md", "txt", "pdf", "docx", "xlsx"]
        )
        if uploaded_file:
            # Save uploaded file to project dir provided by Repo?
            # Design: "Arbitrary directory". "Upload or Load from directory".
            # For upload, we should save it somewhere.
            # V1: Save to project root/uploads
            uploads_dir = os.path.join("projects", str(current_project_id), "uploads")
            os.makedirs(uploads_dir, exist_ok=True)
            file_path = os.path.join(uploads_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            controller.add_file(current_project_id, file_path)
            st.sidebar.success(f"Added {uploaded_file.name}")
            st.rerun()

# --- Main Area ---
st.title("Requirements Review AI")

if not current_project_id:
    st.info("Please select or create a project to begin.")
else:
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Start Analyze", type="primary", use_container_width=True):
            progress_bar = st.progress(0)
            status_text = st.empty()
            callback = UIProgressCallback(progress_bar, status_text)

            with st.spinner("Analyzing..."):
                try:
                    result = controller.run_analysis(current_project_id, callback)
                    st.session_state["last_result"] = result
                    st.session_state["logs"] = callback.logs
                    st.success("Analysis Complete!")
                except Exception as e:
                    st.error(f"Analysis Failed: {e}")
                    import traceback

                    st.error(traceback.format_exc())

    if (
        "last_result" in st.session_state
        and st.session_state["last_result"].project_id == current_project_id
    ):
        result = st.session_state["last_result"]

        # Dashboard Cards
        m = result.metrics
        c1, c2, c3 = st.columns(3)
        c1.metric("Nodes", m.get("node_count"))
        c2.metric("Edges", m.get("edge_count"))
        c3.metric("Defects", len(result.defects))

        tab1, tab2, tab3 = st.tabs(["Visualization", "Defects", "Logs"])

        with tab1:
            graph_data = presenter.present_graph(result.graph)
            # Agraph
            nodes = [Node(**n["data"], **n["style"]) for n in graph_data["nodes"]]
            edges = [Edge(**e["data"], **e["style"]) for e in graph_data["edges"]]

            config = Config(
                width=800,
                height=600,
                directed=True,
                nodeHighlightBehavior=True,
                highlightColor="#F7A7A6",
            )
            agraph(nodes=nodes, edges=edges, config=config)

        with tab2:
            df = presenter.present_defects(result.defects)
            st.dataframe(df, use_container_width=True)

        with tab3:
            st.text_area(
                "Logs", value="\n".join(st.session_state.get("logs", [])), height=300
            )
