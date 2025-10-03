"""
Project Sentinel Dashboard
===========================

Interactive dashboard for visualizing detected events and system metrics.
Built with Streamlit for easy deployment and interaction.

Author: LoopCode
Date: October 2025

Features:
    - Dynamic data folder selection
    - Run event detection from dashboard
    - Real-time event visualization
    - Interactive filtering and analysis

Usage:
    streamlit run dashboard_app.py
"""

import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import sys
import os
import subprocess
import time

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))


def get_default_data_paths():
    """Get list of common data folder paths."""
    base_dir = Path(__file__).parent.parent.parent
    paths = {
        "Competition Data (data/input)": base_dir / "data" / "input",
        "Generated Test Data": base_dir / "tools" / "generated_test_data",
        "Sample Data": base_dir / "data" / "input",
    }
    return {k: str(v) for k, v in paths.items() if v.exists()}


def validate_data_folder(folder_path: str) -> tuple[bool, str]:
    """Validate if the folder contains required data files."""
    folder = Path(folder_path)
    
    if not folder.exists():
        return False, "Folder does not exist"
    
    required_files = [
        'products_list.csv',
        'customer_data.csv'
    ]
    
    required_jsonl = [
        'pos_transactions.jsonl',
        'rfid_readings.jsonl'
    ]
    
    missing_files = []
    for file in required_files:
        if not (folder / file).exists():
            missing_files.append(file)
    
    has_jsonl = any((folder / file).exists() for file in required_jsonl)
    if not has_jsonl:
        missing_files.append("at least one .jsonl file (pos_transactions, rfid_readings, etc.)")
    
    if missing_files:
        return False, f"Missing required files: {', '.join(missing_files)}"
    
    return True, "Valid data folder"


def run_event_detection(data_folder: str, dataset_type: str = "test") -> tuple[bool, str, str]:
    """Run event detection on the selected data folder.
    
    Returns:
        tuple: (success: bool, message: str, events_file: str)
    """
    try:
        # Get the run_demo.py path
        executables_dir = Path(__file__).parent.parent.parent / "evidence" / "executables"
        run_demo_path = executables_dir / "run_demo.py"
        
        if not run_demo_path.exists():
            return False, f"run_demo.py not found at {run_demo_path}", ""
        
        # Run the detection
        cmd = [
            sys.executable,
            str(run_demo_path),
            "--data-dir", data_folder,
            "--dataset-type", dataset_type
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(executables_dir)
        )
        
        if result.returncode == 0:
            # Find the generated events file
            events_file = executables_dir / "results" / "events.jsonl"
            if events_file.exists():
                return True, "Event detection completed successfully!", str(events_file)
            else:
                return False, "Detection ran but no events.jsonl was created", ""
        else:
            error_msg = result.stderr if result.stderr else result.stdout
            return False, f"Detection failed: {error_msg[:500]}", ""
            
    except Exception as e:
        return False, f"Error running detection: {str(e)}", ""


def load_events(events_file: str) -> pd.DataFrame:
    """Load events from JSONL file into DataFrame."""
    events = []
    with open(events_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    
    if not events:
        return pd.DataFrame()
    
    # Flatten event_data into main DataFrame
    df_data = []
    for event in events:
        row = {
            'timestamp': event['timestamp'],
            'event_id': event['event_id'],
            'event_name': event['event_data'].get('event_name', ''),
        }
        # Add all event_data fields
        row.update(event['event_data'])
        df_data.append(row)
    
    df = pd.DataFrame(df_data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df


def create_dashboard(events_file: str = None):
    """Create the main dashboard interface."""
    
    # Page configuration
    st.set_page_config(
        page_title="Project Sentinel Dashboard",
        page_icon="🛡️",
        layout="wide"
    )
    
    # Initialize session state
    if 'events_file' not in st.session_state:
        st.session_state.events_file = events_file
    if 'data_folder' not in st.session_state:
        st.session_state.data_folder = None
    if 'detection_running' not in st.session_state:
        st.session_state.detection_running = False
    
    # Title and header
    st.title("🛡️ Project Sentinel - Event Monitoring Dashboard")
    st.markdown("Real-time monitoring and analysis of self-checkout events")
    st.divider()
    
    # ========================================
    # DATA SOURCE SELECTION SECTION
    # ========================================
    with st.expander("📁 Data Source Configuration", expanded=(st.session_state.events_file is None)):
        st.markdown("### Select Data Input Folder")
        st.markdown("Choose a folder containing sensor data (CSV and JSONL files) to analyze.")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Get available data paths
            default_paths = get_default_data_paths()
            
            # Selection method
            input_method = st.radio(
                "Input Method",
                ["Select from presets", "Enter custom path"],
                horizontal=True
            )
            
            if input_method == "Select from presets":
                if default_paths:
                    selected_preset = st.selectbox(
                        "Choose data folder",
                        options=list(default_paths.keys())
                    )
                    data_folder = default_paths[selected_preset]
                else:
                    st.warning("No preset data folders found. Please use custom path.")
                    data_folder = st.text_input(
                        "Data folder path",
                        value=str(Path(__file__).parent.parent.parent / "data" / "input"),
                        help="Enter the absolute path to your data folder"
                    )
            else:
                data_folder = st.text_input(
                    "Data folder path",
                    value=st.session_state.data_folder or str(Path(__file__).parent.parent.parent / "data" / "input"),
                    help="Enter the absolute path to your data folder containing CSV and JSONL files"
                )
        
        with col2:
            st.markdown("**Dataset Type**")
            dataset_type = st.selectbox(
                "Type",
                ["test", "final"],
                help="Test: For development. Final: For competition submission"
            )
        
        # Validate folder
        if data_folder:
            is_valid, validation_msg = validate_data_folder(data_folder)
            
            if is_valid:
                st.success(f"✅ {validation_msg}")
                st.session_state.data_folder = data_folder
                
                # Show folder contents
                with st.expander("📂 Folder Contents"):
                    folder = Path(data_folder)
                    files = sorted(folder.glob("*"))
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**CSV Files:**")
                        csv_files = [f.name for f in files if f.suffix == '.csv']
                        if csv_files:
                            for f in csv_files:
                                st.text(f"✓ {f}")
                        else:
                            st.text("No CSV files")
                    
                    with col2:
                        st.markdown("**JSONL Files:**")
                        jsonl_files = [f.name for f in files if f.suffix == '.jsonl']
                        if jsonl_files:
                            for f in jsonl_files:
                                st.text(f"✓ {f}")
                        else:
                            st.text("No JSONL files")
                
                # Run detection button
                st.markdown("---")
                col1, col2, col3 = st.columns([2, 1, 2])
                
                with col2:
                    if st.button(
                        "🚀 Run Event Detection",
                        type="primary",
                        disabled=st.session_state.detection_running,
                        use_container_width=True
                    ):
                        st.session_state.detection_running = True
                        with st.spinner("Running event detection... This may take a few minutes."):
                            success, message, events_path = run_event_detection(data_folder, dataset_type)
                            
                            if success:
                                st.success(message)
                                st.session_state.events_file = events_path
                                st.balloons()
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(message)
                        
                        st.session_state.detection_running = False
                
                # Check for existing results
                existing_events = Path(__file__).parent.parent.parent / "evidence" / "executables" / "results" / "events.jsonl"
                if existing_events.exists() and not st.session_state.events_file:
                    st.info(f"💡 Found existing events file. Click below to load it.")
                    if st.button("📊 Load Existing Results"):
                        st.session_state.events_file = str(existing_events)
                        st.rerun()
                
            else:
                st.error(f"❌ {validation_msg}")
                st.info("Please select a valid data folder containing the required files.")
    
    # ========================================
    # EVENTS VISUALIZATION SECTION
    # ========================================
    if not st.session_state.events_file:
        st.info("👆 Please select a data folder and run event detection to view results.")
        st.stop()
    
    events_file = st.session_state.events_file
    
    # Show current events file
    st.markdown(f"**Current Events File:** `{events_file}`")
    st.divider()
    
    # Load events
    try:
        df = load_events(events_file)
        
        if df.empty:
            st.error("No events found in the file!")
            return
        
        # Sidebar filters
        st.sidebar.header("📊 Filters")
        
        # Event type filter
        event_types = ['All'] + sorted(df['event_id'].unique().tolist())
        selected_event = st.sidebar.selectbox("Event Type", event_types)
        
        # Station filter
        if 'station_id' in df.columns:
            stations = ['All'] + sorted(df['station_id'].dropna().unique().tolist())
            selected_station = st.sidebar.selectbox("Station", stations)
        else:
            selected_station = 'All'
        
        # Apply filters
        filtered_df = df.copy()
        if selected_event != 'All':
            filtered_df = filtered_df[filtered_df['event_id'] == selected_event]
        if selected_station != 'All' and 'station_id' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['station_id'] == selected_station]
        
        # Key Metrics Row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Events", len(filtered_df))
        
        with col2:
            fraud_events = len(filtered_df[filtered_df['event_id'].isin(['E001', 'E002', 'E003'])])
            st.metric("Fraud Events", fraud_events)
        
        with col3:
            queue_events = len(filtered_df[filtered_df['event_id'].isin(['E005', 'E006'])])
            st.metric("Queue Issues", queue_events)
        
        with col4:
            if 'station_id' in filtered_df.columns:
                stations_count = filtered_df['station_id'].nunique()
                st.metric("Stations Monitored", stations_count)
            else:
                st.metric("System Crashes", len(filtered_df[filtered_df['event_id'] == 'E004']))
        
        st.divider()
        
        # Event Distribution
        st.subheader("📈 Event Distribution")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Event type distribution
            event_counts = filtered_df['event_id'].value_counts().reset_index()
            event_counts.columns = ['Event ID', 'Count']
            
            st.bar_chart(event_counts.set_index('Event ID'))
            st.caption("Distribution of events by type")
        
        with col2:
            # Event names
            if 'event_name' in filtered_df.columns:
                event_names = filtered_df['event_name'].value_counts().head(10)
                st.bar_chart(event_names)
                st.caption("Top 10 events by name")
        
        st.divider()
        
        # Timeline Analysis
        st.subheader("⏱️ Timeline Analysis")
        
        # Events over time
        filtered_df['hour'] = filtered_df['timestamp'].dt.hour
        events_by_hour = filtered_df.groupby('hour').size().reset_index(name='count')
        
        st.line_chart(events_by_hour.set_index('hour'))
        st.caption("Events by hour of day")
        
        st.divider()
        
        # Station Analysis
        if 'station_id' in filtered_df.columns:
            st.subheader("🏪 Station Analysis")
            
            col1, col2 = st.columns(2)
            
            with col1:
                station_counts = filtered_df['station_id'].value_counts().head(10)
                st.bar_chart(station_counts)
                st.caption("Events by station")
            
            with col2:
                # Event types by station
                if len(filtered_df) > 0:
                    station_event_matrix = pd.crosstab(
                        filtered_df['station_id'], 
                        filtered_df['event_id']
                    )
                    st.dataframe(station_event_matrix, use_container_width=True)
                    st.caption("Event distribution across stations")
        
        st.divider()
        
        # Fraud Analysis
        st.subheader("🚨 Fraud Analysis")
        
        fraud_df = filtered_df[filtered_df['event_id'].isin(['E001', 'E002', 'E003'])]
        
        if len(fraud_df) > 0:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                scanner_avoidance = len(fraud_df[fraud_df['event_id'] == 'E001'])
                st.metric("Scanner Avoidance", scanner_avoidance)
            
            with col2:
                barcode_switching = len(fraud_df[fraud_df['event_id'] == 'E002'])
                st.metric("Barcode Switching", barcode_switching)
            
            with col3:
                weight_discrepancies = len(fraud_df[fraud_df['event_id'] == 'E003'])
                st.metric("Weight Discrepancies", weight_discrepancies)
            
            # Fraud by customer
            if 'customer_id' in fraud_df.columns:
                st.subheader("Fraud by Customer")
                customer_fraud = fraud_df['customer_id'].value_counts().head(10)
                st.bar_chart(customer_fraud)
                st.caption("Top 10 customers with fraud events")
        else:
            st.info("No fraud events detected in the selected period")
        
        st.divider()
        
        # Recent Events Table
        st.subheader("📋 Recent Events")
        
        # Show recent events
        display_columns = ['timestamp', 'event_id', 'event_name']
        if 'station_id' in filtered_df.columns:
            display_columns.append('station_id')
        if 'customer_id' in filtered_df.columns:
            display_columns.append('customer_id')
        
        recent_events = filtered_df.sort_values('timestamp', ascending=False).head(20)
        st.dataframe(
            recent_events[display_columns],
            use_container_width=True,
            hide_index=True
        )
        
        st.divider()
        
        # Download section
        st.subheader("💾 Export Data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # CSV download
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name="sentinel_events.csv",
                mime="text/csv"
            )
        
        with col2:
            # JSON download
            json_str = filtered_df.to_json(orient='records', date_format='iso')
            st.download_button(
                label="📥 Download as JSON",
                data=json_str,
                file_name="sentinel_events.json",
                mime="application/json"
            )
        
        # Footer
        st.divider()
        st.markdown(f"**Data Source:** `{st.session_state.data_folder or 'N/A'}`")
        st.caption("Project Sentinel Dashboard v2.0 | LoopCode | October 2025")
        
    except FileNotFoundError:
        st.error(f"❌ Events file not found: {events_file}")
        st.info("Please run the event detector first to generate events.jsonl")
        if st.button("🔄 Clear and Restart"):
            st.session_state.events_file = None
            st.rerun()
    except Exception as e:
        st.error(f"❌ Error loading events: {str(e)}")
        st.exception(e)
        if st.button("🔄 Clear and Restart"):
            st.session_state.events_file = None
            st.rerun()


def main():
    """Main entry point for the dashboard."""
    # Check if events file is provided via command line (backward compatibility)
    events_file = None
    
    if len(sys.argv) > 1 and '--events-file' in sys.argv:
        import argparse
        parser = argparse.ArgumentParser(description='Project Sentinel Dashboard')
        parser.add_argument('--events-file', help='Path to events.jsonl file')
        args, unknown = parser.parse_known_args()
        events_file = args.events_file
    
    # Create dashboard
    create_dashboard(events_file)


if __name__ == '__main__':
    main()
