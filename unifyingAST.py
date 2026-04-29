import streamlit as st
import re

############################################################
# AST NODE
############################################################

class ASTNode:
    def __init__(self, node_type, value=None, file=None):
        self.type = node_type
        self.value = value
        self.file = file
        self.children = []

    def add(self, node):
        self.children.append(node)

############################################################
# CLEAN COMMENTS
############################################################

def remove_comments(text):
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)

############################################################
# TOKENIZER
############################################################

def tokenize(text):

    tokens = []

    for line in text.splitlines():
        line = line.strip()
        if line:
            tokens.append(line)

    return tokens

############################################################
# TCL PARSER
############################################################

def parse_tcl_content(content, filename):

    content = remove_comments(content)
    tokens = tokenize(content)

    root = ASTNode("FILE", filename)

    current_block = root
    stack = []

    for line in tokens:

        # INCLUDE
        if line.startswith("INCLUDE"):
            node = ASTNode("INCLUDE", line.split()[1], filename)
            current_block.add(node)

        # PROC
        elif line.startswith("PROC"):
            name = line.replace("PROC", "").replace(";", "").strip()
            node = ASTNode("PROC", name, filename)
            current_block.add(node)
            stack.append(current_block)
            current_block = node

        # SUBR
        elif line.startswith("SUBR"):
            name = line.replace("SUBR", "").strip()
            node = ASTNode("SUBR", name, filename)
            current_block.add(node)
            stack.append(current_block)
            current_block = node

        # STEP LABEL
        elif re.match(r"\d+:", line):
            step_id = line.split(":")[0]
            node = ASTNode("STEP_LABEL", step_id, filename)
            current_block.add(node)
            stack.append(current_block)
            current_block = node

        # STEP BLOCK
        elif line.startswith("STEP"):
            node = ASTNode("STEP", line, filename)
            current_block.add(node)
            stack.append(current_block)
            current_block = node

        # BEGIN
        elif line.startswith("BEGIN"):
            node = ASTNode("BEGIN", None, filename)
            current_block.add(node)
            stack.append(current_block)
            current_block = node

        # END
        elif line.startswith("END"):
            if stack:
                current_block = stack.pop()

        # DECL SECTIONS
        elif line.startswith(("VAR", "VARTAG", "DBVAR", "UNITS")):
            node = ASTNode("DECL_SECTION", line, filename)
            current_block.add(node)

        # COMMAND
        else:
            node = ASTNode("COMMAND", line, filename)
            current_block.add(node)

    return root

############################################################
# BUILD PROJECT AST (MULTI FILE)
############################################################

def build_project_ast(uploaded_files):

    project = ASTNode("PROJECT")

    for file in uploaded_files:

        content = file.read().decode(errors="ignore")
        ast = parse_tcl_content(content, file.name)
        project.add(ast)

    return project

############################################################
# FAST AST TEXT BUILDER
############################################################

def build_ast_text(node, level=0):

    text = "  " * level + f"{node.type}: {node.value}\n"

    for child in node.children:
        text += build_ast_text(child, level + 1)

    return text

############################################################
# SYMBOL TABLE
############################################################

def build_symbol_table(project):

    symbols = {}

    for file in project.children:
        for node in file.children:
            if node.type in ["PROC", "SUBR"]:
                symbols[node.value] = node.file

    return symbols

############################################################
# STREAMLIT UI
############################################################

st.set_page_config(layout="wide")

st.title("ABB AdvaBuild TCL → Unified AST Generator")

uploaded_files = st.file_uploader(
    "Upload Multiple TCL Files",
    type=["tcl"],
    accept_multiple_files=True
)

if uploaded_files:

    with st.spinner("Parsing TCL project..."):

        project_ast = build_project_ast(uploaded_files)

        symbols = build_symbol_table(project_ast)

        ast_text = build_ast_text(project_ast)

    st.success("Unified AST Generated")

    col1, col2 = st.columns([1,2])

    with col1:
        st.subheader("Procedures / Subroutines")
        st.json(symbols)

    with col2:
        st.subheader("Unified AST")
        st.text_area("AST View", ast_text, height=700)
