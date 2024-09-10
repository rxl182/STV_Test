# Import Python standard packages from PyPi [https://pypi.org/]
# If you need to reference in any other standard packages, import them here.
# Added packages should also be added to the 'requirements.txt'
# Use command line 'pip install -r requirements.txt' to install into your virtual environment
import pandas as pd
import streamlit as st

# Import local *.py files as reference modules to be utilized in the calculation
import units  # units.py: No changes to units.py will be accepted, unless use case is fully justified.

# import formulas  # formulas.py: For this simple 'SingleCalc' we will be writing the information directly on this page.


# -----------------------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------------------
# This is the section your looking for to update your calculation.
# -----------------------------------------------------------------------------------------------------------
# Python will read in this section line by line and perform the action
# The order in which you arrange will directly correlate to what is printed to the webapp
# The calculation header, description, assumptions, etc. have already been loaded in at this point
# from within the 'information.md' file.

# The script is set up to start in the ```run``` procedure. However, we will first create our own procedures that we will use in our calculation.
# In the ```MultiCalc``` example, these would be contained within their associated class objects within the formulas module.
def markdown():
    md = """
    The formula for wire resistance is:

    $R_{wire} = 2 \\times n_{conductors} \\times L_{wire} \\times R_{length}$
    
    The formula for voltage at the load is:

    $V_{load} = V_{source} - I_{wire} \\times R_{wire}$
    """
    return md


def voltage_at_load(v_in, r, i):
    """
    Calculate the voltage at the load after the voltage drop across the wire.
    
    :param v_in: Voltage at the source (in volts)
    :param r: Total resistance of the wire (in ohms)
    :param i: Current flowing through the wire (in amperes)
    
    :return: Voltage at the load (in volts)
    """
    # Calculate the voltage drop (Ohm's Law: V_drop = I * R)
    v_drop  = i * r
    
    # Calculate the voltage at the load
    v_load = v_in - v_drop
    v_pct = (1 - v_load / v_in) * 100 if v_drop != 0 else 0

    return v_load, units.load(str(v_pct) + ' percent')

def parse_csv(file_path):
    """
    Parses a CSV file containing wire resistance data into a pandas DataFrame.
    Assumes the first line of the CSV contains column headers.
    
    :param file_path: Path to the CSV file (default is 'wire_resistance.csv')
    :return: A pandas DataFrame with the inferred column names from the file
    """
    try:
        # Read the CSV file, letting pandas infer the column names from the first row
        df = pd.read_csv(file_path)
        return df
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except pd.errors.EmptyDataError:
        print("Error: The file is empty.")
    except pd.errors.ParserError:
        print("Error: There was an issue parsing the file.")

# Function to initialize or reset the DataFrame with dynamic columns in the session state
def initialize_data(session_state_ref, sst_key, headers):
    if sst_key not in session_state_ref:
        session_state_ref[sst_key] = pd.DataFrame(columns=headers)
    return session_state_ref[sst_key]

def clear_data(session_state_ref, sst_key, headers):
    session_state_ref[sst_key] = pd.DataFrame(columns=headers)

def return_max(_list):
    _min = min(_list)
    _max = max(_list)
    return _max if abs(_max) > abs(_min) else _min

# Now that we have all the functions setup we intend to utilize, lets look into how we want the input/results rendered on the website.
# For this, we are utilizing streamlit.
def run():
    wire_df = parse_csv('wire_resistance.csv')

    # Section Header for input Data
    st.markdown('### Input')
    source_voltage = units.input('Source DC', '24.0 volts', minor=False)
    load_current = units.input('Current Draw', '1.0 ampere', minor=False)

    # Enable the download/upload of custom wire characteristics
    with st.expander('Upload Wire Data', expanded = False):
        col_1, col_2 = st.columns([4, 1])
        with col_2:
            st.container(height=20, border=False)
            st.download_button(
                label='download sample csv',
                data=wire_df.to_csv(index=False).encode('utf-8'),
                file_name='sample_wire_resistance.csv',
                mime='textcsv'
            )
        with col_1:
            upload_file = st.file_uploader(
                'Upload a properly formatted csv file containing wire properties',
                type={'csv'},
                accept_multiple_files=False)
            if upload_file is not None:
                upload_df = parse_csv(upload_file)
                vals = [oheader in upload_df.columns for oheader in wire_df.columns]
                if not all(vals):
                    st.warning('The headers need to remain from the sample download. Try again.')
                else:
                    st.success('Wire Table updated!')
                    wire_df = upload_df

    wire_col1, wire_col2 = st.columns(2)
    with wire_col1:
        number_of_conductors = st.number_input('Number of Conductors', min_value=1, step=1)
    with wire_col2:
        # Create a dropdown (select box) using Streamlit
        selected_awg = st.selectbox(
            'Wire Size (AWG):',
            wire_df['awg'],
            index=10
        )

    wire_length = units.input('Length of Wire', '300 ft', minor=False)

    # Filter the DataFrame to get the row where 'awg' equals the selected_awg
    selected_row = wire_df[wire_df['awg'] == selected_awg]
    # Extract the 'r_25c' value for the selected AWG
    wire_resistivity = units.load(str(selected_row['r_25c'].values[0]) + ' ohm/kft')

    total_resistance = 2 * wire_length * wire_resistivity / units.load('1000 ft/kft') / number_of_conductors
    st.caption(f'Wire Resistance = {units.unitdisplay(total_resistance, minor=False)}')

    # Section Header for Results
    st.markdown('---')
    st.markdown('### Results')
    
    load_voltage, pct_drop = voltage_at_load(source_voltage, total_resistance, load_current)
    st.write('$V_{load}= $'+ f' {units.unitdisplay(load_voltage, minor=False)} ({units.unitdisplay(pct_drop, minor=False)} drop)')

    # Initialize the DataFrame in session state if not already present
    voltage_record_key = 'recorded_data'
    voltage_record_headers = ['Source Voltage', 'Load Current', 'Number of Conductors', 'Conductor Size',
                              'Conductor Length', 'Load Voltage', 'Percent Drop']
    initialize_data(st.session_state, voltage_record_key, voltage_record_headers)

    voltage_record_values = [source_voltage, load_current, number_of_conductors,
                             selected_awg, wire_length, load_voltage, pct_drop]
    new_voltage_record = dict(zip(voltage_record_headers, voltage_record_values))

    # Button to add the current values to the record (DataFrame)
    if st.button("Add to Record"):
        st.session_state[voltage_record_key] = pd.concat([st.session_state[voltage_record_key],
                                                          pd.DataFrame([new_voltage_record])],
                                                          ignore_index=True)

    # Display the recorded data
    if not st.session_state[voltage_record_key].empty:
        st.dataframe(st.session_state[voltage_record_key])

        st.button("Clear Records", on_click=clear_data, args=(st.session_state,
                                                              voltage_record_key,
                                                              voltage_record_headers))

    st.markdown('---')
    # Let's present the formulas we want to utilize using markdown notation.
    # Visit 'https://www.upyesp.org/posts/makrdown-vscode-math-notation/' for information
    st.markdown(markdown())

# -----------------------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------------------


# Don't revise. Changes to your calculation title and instructions should be made within the 'information.md' file.
def setup():
    # This is where the markdown information for the calculation title, description, etc. is loaded in.
    with open('information.md', 'r') as f:
        header = f.read()
    st.write(header)
    run()


# Don't revise. Run setup() if this file is the entry
if __name__ == '__main__':
    st.set_page_config(
        page_title='STV_Test Calculation Set',
        layout='wide'
    )
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        setup()
