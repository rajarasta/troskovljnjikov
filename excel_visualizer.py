import streamlit as st
import pandas as pd
import numpy as np
import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import base64
import os


def load_excel_data(file_path_or_buffer, sheet_name=None):
    """
    Load Excel data with multiple options for different file types
    """
    try:
        # Try to read with pandas first
        if isinstance(file_path_or_buffer, str):
            df = pd.read_excel(file_path_or_buffer, sheet_name=sheet_name, engine='openpyxl')
        else:
            df = pd.read_excel(file_path_or_buffer, sheet_name=sheet_name, engine='openpyxl')
        
        return df
    except Exception as e:
        st.error(f"Error loading Excel file: {str(e)}")
        return None


def display_excel_summary(df):
    """
    Display a summary of the Excel data
    """
    st.subheader("📊 Data Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Rows", df.shape[0])
    with col2:
        st.metric("Columns", df.shape[1])
    with col3:
        st.metric("Missing Values", df.isnull().sum().sum())
    with col4:
        st.metric("Memory Usage", f"{df.memory_usage(deep=True).sum() / 1024:.2f} KB")
    
    st.write("**Column Information:**")
    col_info = pd.DataFrame({
        'Data Type': df.dtypes,
        'Non-Null Count': df.count(),
        'Null Count': df.isnull().sum(),
        '% Null': (df.isnull().sum() / len(df)) * 100
    })
    st.dataframe(col_info, use_container_width=True)


def display_data_table(df):
    """
    Display the actual data table with pagination and filtering
    """
    st.subheader("📋 Raw Data Table")
    
    # Pagination
    rows_per_page = st.slider("Rows per page", min_value=5, max_value=100, value=20)
    total_pages = len(df) // rows_per_page + 1
    
    if total_pages > 1:
        current_page = st.selectbox("Page", options=list(range(1, total_pages + 1)), format_func=lambda x: f"Page {x}")
        start_idx = (current_page - 1) * rows_per_page
        end_idx = start_idx + rows_per_page
        df_page = df.iloc[start_idx:end_idx]
    else:
        df_page = df
    
    # Search/filter functionality
    search_col = st.selectbox("Filter by column", options=["None"] + df.columns.tolist())
    if search_col != "None":
        search_term = st.text_input(f"Search in {search_col}")
        if search_term:
            mask = df[search_col].astype(str).str.contains(search_term, case=False, na=False)
            df_page = df[mask].iloc[start_idx:end_idx] if len(df[mask]) > start_idx else df[mask]
    
    st.dataframe(df_page, use_container_width=True, height=500)


def visualize_numeric_data(df):
    """
    Create visualizations for numeric columns
    """
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    if numeric_cols:
        st.subheader("📈 Numeric Data Visualizations")
        
        # Distribution plots
        selected_num_col = st.selectbox("Select numeric column for distribution", numeric_cols)
        if selected_num_col:
            fig = px.histogram(df, x=selected_num_col, title=f"Distribution of {selected_num_col}")
            st.plotly_chart(fig, use_container_width=True)
        
        # Correlation heatmap if there are multiple numeric columns
        if len(numeric_cols) > 1:
            st.subheader("🔗 Correlation Heatmap")
            corr_df = df[numeric_cols].corr()
            fig = px.imshow(corr_df, 
                           text_auto=True, 
                           aspect="auto",
                           title="Correlation Matrix")
            st.plotly_chart(fig, use_container_width=True)


def visualize_categorical_data(df):
    """
    Create visualizations for categorical columns
    """
    categorical_cols = df.select_dtype(include=['object']).columns.tolist()
    
    if categorical_cols:
        st.subheader(" PIE Charts for Categorical Data")
        
        selected_cat_col = st.selectbox("Select categorical column for pie chart", categorical_cols)
        if selected_cat_col:
            value_counts = df[selected_cat_col].value_counts()
            fig = px.pie(values=value_counts.values, names=value_counts.index, 
                        title=f"Distribution of {selected_cat_col}")
            st.plotly_chart(fig, use_container_width=True)


def display_advanced_features(df):
    """
    Display advanced features like sorting, grouping, etc.
    """
    st.subheader("⚙️ Advanced Data Operations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        sort_col = st.selectbox("Sort by column", options=["None"] + df.columns.tolist())
        if sort_col != "None":
            ascending = st.checkbox("Ascending", value=True)
            df_sorted = df.sort_values(by=sort_col, ascending=ascending)
            st.dataframe(df_sorted.head(10), use_container_width=True)
    
    with col2:
        group_col = st.selectbox("Group by column", options=["None"] + df.columns.tolist())
        if group_col != "None":
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if numeric_cols:
                agg_col = st.selectbox("Aggregate column", options=["None"] + numeric_cols)
                if agg_col != "None":
                    agg_func = st.selectbox("Aggregation function", ["mean", "sum", "count", "std", "min", "max"])
                    grouped_df = df.groupby(group_col)[agg_col].agg(agg_func).reset_index()
                    st.dataframe(grouped_df, use_container_width=True)


def create_download_link(df, filename="excel_data.csv"):
    """
    Create a download link for the processed data
    """
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">Download CSV File</a>'
    st.markdown(href, unsafe_allow_html=True)


def main():
    """
    Main function to run the Excel viewer app
    """
    st.set_page_config(page_title="Excel Data Viewer", layout="wide")
    st.title("📊 Professional Excel Data Viewer")
    st.markdown("""
    Upload an Excel file to explore, analyze, and visualize your data in an attractive and interactive way.
    """)
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose an Excel file", 
        type=["xlsx", "xls"],
        accept_multiple_files=False
    )
    
    if uploaded_file is not None:
        st.success(f"Successfully loaded: {uploaded_file.name}")
        
        # Load the data
        df = load_excel_data(uploaded_file)
        
        if df is not None:
            # Tabs for different views
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "📊 Summary", 
                "📋 Data Table", 
                "📈 Visualizations", 
                "⚙️ Advanced", 
                "💾 Export"
            ])
            
            with tab1:
                display_excel_summary(df)
            
            with tab2:
                display_data_table(df)
            
            with tab3:
                col1, col2 = st.columns(2)
                with col1:
                    visualize_numeric_data(df)
                with col2:
                    visualize_categorical_data(df)
            
            with tab4:
                display_advanced_features(df)
            
            with tab5:
                st.subheader("Export Options")
                st.write("Download your processed data in various formats:")
                create_download_link(df, f"{uploaded_file.name.split('.')[0]}_processed.csv")
                
                # Option to export specific view
                if st.button("Export Current View as CSV"):
                    st.download_button(
                        label="Download Current Data View",
                        data=df.to_csv(index=False).encode('utf-8'),
                        file_name=f"{uploaded_file.name.split('.')[0]}_view.csv",
                        mime='text/csv'
                    )
        else:
            st.error("Failed to load the Excel file. Please check the file format.")
    else:
        st.info("Please upload an Excel file (.xlsx or .xls) to begin exploring your data.")
        
        # Provide option to analyze existing Excel files in the directory
        excel_dir = "/media/josip-rastocic/DrugiDisk/Programi/troskovljnjikov/vanjski-podaci/primjeri-excel-ponuda"
        if os.path.exists(excel_dir):
            st.subheader("Or analyze existing Excel files in the project directory")
            excel_files = [f for f in os.listdir(excel_dir) if f.endswith(('.xlsx', '.xls'))]
            
            if excel_files:
                selected_file = st.selectbox("Select an existing Excel file to analyze:", excel_files)
                if selected_file and st.button("Load Selected File"):
                    file_path = os.path.join(excel_dir, selected_file)
                    df = load_excel_data(file_path)
                    
                    if df is not None:
                        # Store in session state to persist across reruns
                        st.session_state.df = df
                        st.session_state.filename = selected_file
                        st.experimental_rerun()


if __name__ == "__main__":
    main()