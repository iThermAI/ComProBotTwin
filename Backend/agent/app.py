from __future__ import print_function
from pymongo import MongoClient
from copy import deepcopy
from datetime import datetime, timedelta
import os.path
import sys
import numpy as np
import sklearn as sk
from sklearn.svm import SVR
import time
import pandas as pd
import requests
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    filename="agent_logs.log",
)


DEFAUL_MAINTEANCE_PUMP = 45
DEFAUL_MAINTEANCE_FILTER = 21
DAYS_BETWEEN_SAME_ALERTS = 1
PUMP_MALFUNCTION_ALERT_DAYS = 5
DELAY_FILTER_LIFE = 4 #(CYCLE)

ZEROS_THRESHOLD = 5

# ! It should be set to a reletively high value compared to the period of the pump speed
DELAY = 15  # Also Window size (SECOND)
BEGINNING_WINDOW_SIZE_FOR_BLOCKAGE_CHECK = 5  # (SECOND)
PER_SECONDS_READS = 10

ALL_COLUMNS = ['_id', 'time', 'Barr_pulses', 'Gelcoat_pulses', 'Barrier_speedRPM',
               'Gelcoat_speedRPM', 'WaterLevel_1', 'WaterLevel_2', 'Pressure']

COLUMNS_TO_CHECK_SPEED = {
    "gelcoat": "Gelcoat_speedRPM",
    "barrier": "Barrier_speedRPM"
}

COLUMNS_TO_CHECK_PULSES = {
    "gelcoat": "Gelcoat_pulses",
    "barrier": "Barr_pulses"
}


PUMP_VOLUME = 150
PULSE_PER_FULL_STROKE = 10.17
GELCOAT_SPEC_WEIGHT = 1.33

#! IN THE INITIAL CODE THERE WERE NO SEPERATE WEIGHT_PER_PULSE VALUES FOR GELCOAT AND BARRIER
WEIGHT_PER_PULSE_GELCOAT = PUMP_VOLUME / \
    PULSE_PER_FULL_STROKE * GELCOAT_SPEC_WEIGHT / 100
WEIGHT_PER_PULSE_BARRIER = PUMP_VOLUME / \
    PULSE_PER_FULL_STROKE * GELCOAT_SPEC_WEIGHT / 100

COLUMNS_WEIGHT_PER_PULSE = {
    "gelcoat": WEIGHT_PER_PULSE_GELCOAT,
    "barrier": WEIGHT_PER_PULSE_BARRIER
}


client = MongoClient("mongodb://db:27017")

try:
    _ = client.server_info()
except:
    print("*"*100)
    print("AGENT CANNOT CONNECT TO MONGODB")
    print("*"*100)
    logging.critical("AGENT CANNOT CONNECT TO MONGODB")


db_sensor_data = client["Sensor_Data"]
collection_sensor_data = db_sensor_data["test_28_march"]

db_agent_nominal_values = client["Agent_Nominal_Values"]
collection_nominal_gelcoat = db_agent_nominal_values["gelcoat"]
collection_nominal_barrier = db_agent_nominal_values["barrier"]

db_agent_cycle_history = client["Agent_Cycle_History"]
collection_alerts = db_agent_cycle_history["alerts"]
collection_alerts_nominal_values = db_agent_cycle_history["alerts_nominal_values"]

db_agent_maintenance = client["Agent_Maintenance"]
collection_maintenance_pump = db_agent_maintenance["maintenance_pump"]
collection_maintenance_filter = db_agent_maintenance["maintenance_filter"]

db_sessions = client["Sessions"]
collection_sessions = db_sessions["sessions"]
collection_products = db_sessions["products"]
collection_delete_useless_reads = db_sessions["delete_useless_reads"]


def add_alert(message, more_info=None, nominal_value=False):
    """
    Adds an alert to the collection based on the given parameters.

    Args:
        message (str): The message of the alert.
        more_info (str, optional): Additional information about the alert. Defaults to None.
        nominal_value (bool, optional): Indicates if the alert is a nominal value alert. Defaults to False.
    """
    
    time_now = datetime.now()
    alert = {
        "time": time_now,
        "message": message,
        "more_info": more_info
    }
    if nominal_value:
        collection_alerts_nominal_values.insert_one(alert)
        logging.info(f"Nominal Value Alert Added\nTime: {time_now}\nMessage: {message}\nMore Info: {more_info}")
    else:
        collection_alerts.insert_one(alert)
        logging.info(f"Alert Added\n Time: {time_now}\n Message: {message}\n More Info: {more_info}")
    pass


def get_nominal_value_pressure_gelcoat():
    """
    Retrieves the nominal value for pressure in the gelcoat process.

    Returns:
        float: The nominal pressure value.

    Raises:
        LookupError: If no nominal value is found for pressure (gelcoat).
    """
    # get all records from collection_nominal_gelcoat as pandas dataFrame
    nominal_runs = pd.DataFrame(collection_nominal_gelcoat.find())
    if len(nominal_runs): 

        # nominal pressure is the mean of the column named avg_pressure
        nominal_pressure = nominal_runs['avg_pressure'].mean()
        return nominal_pressure                                           
    else:
        # raise a relevant error after adding an alert in the database
        add_alert(
            "No nominal value found for pressure (gelcoat). Can't check whether Pressure is sufficient.",
            nominal_value=True
        )
        raise LookupError("No nominal value found for pressure (gelcoat)")


def get_nominal_value_pressure_barrier():
    """
    Retrieves the nominal value for pressure (barrier) from the database.

    Returns:
        float: The nominal pressure value.

    Raises:
        LookupError: If no nominal value is found for pressure (barrier).
    """
    
    # get all records from collection_nominal_barrier as pandas dataFrame
    nominal_runs = pd.DataFrame(collection_nominal_barrier.find())
    if len(nominal_runs):
        
        # nominal pressure is the mean of the column named avg_pressure
        nominal_pressure = nominal_runs['avg_pressure'].mean()
        return nominal_pressure
    else:
        # raise a relevant error after adding an alert in the database
        add_alert(
            "No nominal value found for pressure (barrier). Can't check whether Pressure is sufficient.",
            nominal_value=True
        )
        raise LookupError("No nominal value found for pressure (barrier)")

def get_nominal_value_sprayed_barrier():
    """
    Retrieves the nominal value for the sprayed amount of a barrier.

    Returns:
        float: The nominal sprayed amount.

    Raises:
        LookupError: If no nominal value is found for the sprayed amount.
    """
    
    # get all records from collection_nominal_barrier as pandas dataFrame
    nominal_runs = pd.DataFrame(collection_nominal_barrier.find())
    if len(nominal_runs):
        
        # nominal sprayed amount is the mean of the column named sprayed_amount
        nominal_sprayed = nominal_runs['total_sprayed_amount'].mean()
        return nominal_sprayed
    else:
        # raise a relevant error after adding an alert in the database
        add_alert(
            "No nominal value found for sprayed amount (barrier). Can't check whether Sprayed amount is sufficient.",
            nominal_value=True
        )
        raise LookupError("No nominal value found for sprayed amount (barrier)")
    
def get_nominal_value_sprayed_gelcoat():
    """
    Retrieves the nominal value for the sprayed amount of gelcoat.

    Returns:
        float: The nominal sprayed amount of gelcoat.

    Raises:
        LookupError: If no nominal value is found for the sprayed amount of gelcoat.
    """
    
    # get all records from collection_nominal_gelcoat as pandas dataFrame
    nominal_runs = pd.DataFrame(collection_nominal_gelcoat.find())
    if len(nominal_runs):
            
        # nominal sprayed amount is the mean of the column named sprayed_amount
        nominal_sprayed = nominal_runs['total_sprayed_amount'].mean()
        return nominal_sprayed
    else:
        # raise a relevant error after adding an alert in the database
        add_alert(
            "No nominal value found for sprayed amount (gelcoat). Can't check whether Sprayed amount is sufficient.",
            nominal_value=True
        )
        raise LookupError("No nominal value found for sprayed amount (gelcoat)")
    
def get_nominal_value_speed_gelcoat():
    """
    Retrieves the nominal value for the speed of gelcoat.

    Returns:
        float: The nominal speed value for gelcoat.

    Raises:
        LookupError: If no nominal value is found for speed (gelcoat).
    """
    
    # get all records from collection_nominal_gelcoat as pandas dataFrame
    nominal_runs = pd.DataFrame(collection_nominal_gelcoat.find())
    if len(nominal_runs):
        
        # nominal speed is the mean of the column named avg_speed
        nominal_speed = nominal_runs['avg_speed'].mean()
        return nominal_speed
    else:
        # raise a relevant error after adding an alert in the database
        add_alert(
            "No nominal value found for speed (gelcoat). Can't check whether Speed is sufficient.",
            nominal_value=True
        )
        raise LookupError("No nominal value found for speed (gelcoat)")
    
    
def get_nominal_value_speed_barrier():
    """
    Retrieves the nominal value for speed (barrier) from the database.

    Returns:
        float: The nominal speed value.

    Raises:
        LookupError: If no nominal value is found for speed (barrier).
    """
    
    # get all records from collection_nominal_barrier as pandas dataFrame
    nominal_runs = pd.DataFrame(collection_nominal_barrier.find())
    if len(nominal_runs):
        
        # nominal speed is the mean of the column named avg_speed
        nominal_speed = nominal_runs['avg_speed'].mean()
        return nominal_speed
    else:
        # raise a relevant error after adding an alert in the database
        add_alert(
            "No nominal value found for speed (barrier). Can't check whether Speed is sufficient.",
            nominal_value=True
        )
        raise LookupError("No nominal value found for speed (barrier)")
    


def check_blockage(pump_type, cycle_data, window_data):
    """
    Checks for blockage in the spraygun based on the given pump type, cycle data, and window data.

    Args:
        pump_type (str): The type of pump.
        cycle_data (DataFrame): The data for the entire cycle.
        window_data (DataFrame): The data for the current window.

    Returns:
        None
    """
    try:
        if len(cycle_data) > BEGINNING_WINDOW_SIZE_FOR_BLOCKAGE_CHECK*PER_SECONDS_READS:
            column_name = COLUMNS_TO_CHECK_SPEED[pump_type]
            # Check if there was a 20 percent drop in avg speed of window, but not in the pressure of the window
            starting_window = cycle_data[:BEGINNING_WINDOW_SIZE_FOR_BLOCKAGE_CHECK*PER_SECONDS_READS]
            if starting_window[column_name].mean() * 0.8 > window_data[column_name].mean() and starting_window['Pressure'].mean() * 0.9 < window_data['Pressure'].mean():
                # ADD ALERT partial_spraygun_blockage
                add_alert("Partial Spraygun Blockage",
                        f'pump_type: {pump_type}, average speed of the window: {window_data[column_name].mean()}, average pressure of the window: {window_data["Pressure"].mean()}, average speed of the starting window: {starting_window[column_name].mean()}, average pressure of the starting window: {starting_window["Pressure"].mean()}')
                pass
            elif starting_window[column_name].mean() * 0.1 > window_data[column_name].mean() and starting_window['Pressure'].mean() * 0.4 < window_data['Pressure'].mean():
                # ADD ALERT partial_spraygun_blockage
                add_alert("Total Spraygun Blockage",
                        f'pump_type: {pump_type}, average speed of the window: {window_data[column_name].mean()}, average pressure of the window: {window_data["Pressure"].mean()}, average speed of the starting window: {starting_window[column_name].mean()}, average pressure of the starting window: {starting_window["Pressure"].mean()}')
                pass
    except Exception as e:
        pass


def check_pressure(window_data, pump_type):
    """
    Checks the pressure of a pump based on the given window data and pump type.
    
    Args:
        window_data (dict): A dictionary containing the window data.
        pump_type (str): The type of pump to check the pressure for.
        
    Raises:
        ValueError: If an invalid pump type is provided.
        
    Returns:
        None
    """
    
    try:
        if pump_type == "gelcoat":
            nominal_value_pressure = get_nominal_value_pressure_gelcoat()
        elif pump_type == "barrier":
            nominal_value_pressure = get_nominal_value_pressure_barrier()
        else:
            raise ValueError(
                f"Invalid pump type, it should be either gelcoat or barrier. {pump_type} is given.")

        if window_data['Pressure'].mean() < nominal_value_pressure * 0.9:
            # if there was a recent alert of the same case, don't add a new one
            last_alert = collection_alerts.find_one({"message": f"Insufficient Pressure of {pump_type} pump"})
            if not last_alert:
                add_alert(f"Insufficient Pressure of {pump_type} pump",
                      f'average pressure of the window: {window_data["Pressure"].mean()}, nominal value of the pressure: {nominal_value_pressure}')
                
            elif datetime.now() - last_alert['time'] > timedelta(days=DAYS_BETWEEN_SAME_ALERTS):
                add_alert(f"Insufficient Pressure of {pump_type} pump",
                        f'average pressure of the window: {window_data["Pressure"].mean()}, nominal value of the pressure: {nominal_value_pressure}')
    except LookupError as e:
        pass

def add_first_maintenance_recored():
    """
    Adds the default maintenance records for pumps and filters if they are empty.

    This function checks if the maintenance records for pumps and filters are empty.
    If they are empty, it adds the default maintenance records with start time as now
    and end time as a specified number of days later.

    Parameters:
        None

    Returns:
        None
    """
    
    # check if the maintenance records are empty
    if collection_maintenance_pump.count_documents({}) < 2:
        # add the default maintenance record, start time is now and end time is 45 days later
        collection_maintenance_pump.insert_one(
            {
                "start_time": datetime.now(),
                "end_time": datetime.now() + timedelta(days=DEFAUL_MAINTEANCE_PUMP),
                "pump_type": "gelcoat"
            }
        )
        collection_maintenance_pump.insert_one(
            {
                "start_time": datetime.now(),
                "end_time": datetime.now() + timedelta(days=DEFAUL_MAINTEANCE_PUMP),
                "pump_type": "barrier"
            }
        )
    if collection_maintenance_filter.count_documents({}) < 2:
        # add the default maintenance record, start time is now and end time is 21 days later
        collection_maintenance_filter.insert_one(
            {
                "start_time": datetime.now(),
                "end_time": datetime.now() + timedelta(days=DEFAUL_MAINTEANCE_FILTER),
                "pump_type": "gelcoat"
            }
        )
        collection_maintenance_filter.insert_one(
            {
                "start_time": datetime.now(),
                "end_time": datetime.now() + timedelta(days=DEFAUL_MAINTEANCE_FILTER),
                "pump_type": "barrier"
            }
        )

def check_pump_malfunction(pump_type):
    """
    Checks for pump malfunction based on the sprayed amount deviation from nominal values.
    
    Args:
        pump_type (str): The type of pump. It should be either "gelcoat" or "barrier".
        
    Raises:
        ValueError: If an invalid pump type is given.
        
    Returns:
        None
    """
    
    try:
        # check the last 10 records of the cycle data
        # if the deviation in the sprayed amount of 2 consecutive cycles from nominal values are more than 15%,  add an alert for maintenance.
        
        requests.get("http://api:5000/api/get_new_sessions")       
        
        if pump_type == "gelcoat":
            nominal_value = get_nominal_value_sprayed_gelcoat()
        elif pump_type == "barrier":
            nominal_value = get_nominal_value_sprayed_barrier()
        else:
            raise ValueError(
                "Invalid pump type, it should be either gelcoat or barrier. <{pump_type}> is given.")

        recent_sessions = pd.DataFrame(
            collection_sessions.find({"pump_type":pump_type}).sort([("_id", -1)]).limit(10)
        )

        # Calculate the deviation of the sprayed amount from the nominal value for each record
        recent_sessions['spray_deviation'] = (recent_sessions['total_sprayed_amount'] - nominal_value) / (nominal_value + 0.00001)
        

        # if there are more than 5 records with deviation more than 15%, add an alert for immediate maintenance, only if its already more than 1 days
        if recent_sessions["spray_deviation"].apply(lambda x: x > 0.15).sum() > 5:
            # check the remaining time for maintenance, if the remaining time is more than 1 day, add an alert for immediate maintenance
            maintenance_record = collection_maintenance_pump.find_one({"pump_type": pump_type})
            if maintenance_record['end_time'] - datetime.now() > timedelta(days=1):
                collection_maintenance_pump.update_one(
                    {"_id": maintenance_record['_id']},
                    {"$set": {"end_time": datetime.now() + timedelta(days=PUMP_MALFUNCTION_ALERT_DAYS)}}
                )
                add_alert(f"{pump_type} Pump Malfunction (Immediate)",
                    f"More than 5 records with deviation more than 15%: {recent_sessions['spray_deviation']}")
            # in case there are less than 1 day remaining for maintenance, check if there is already an alert added whithin last 24 hours for maintenance in order to prevent spamming
            else:
                last_alert = collection_alerts.find_one({"message": f"{pump_type} Pump Malfunction (Immediate)"})
                if not last_alert:
                    add_alert(f"{pump_type} Pump Malfunction (Immediate)",
                        f"More than 5 records with deviation more than 15%: {recent_sessions['spray_deviation']}")
                elif datetime.now() - last_alert['time'] > timedelta(days=DAYS_BETWEEN_SAME_ALERTS):
                    add_alert(f"{pump_type} Pump Malfunction (Immediate)",
                        f"More than 5 records with deviation more than 15%: {recent_sessions['spray_deviation']}")
        

        # if the deviation is more than 15% for 2 consecutive cycles, add an alert for maintenance, and change the maintenace end time to 5 days later, only if its already more than 5 days
        if recent_sessions['spray_deviation'].iloc[0] > 0.15 and recent_sessions['spray_deviation'].iloc[1] > 0.15:
            # check the remaining time for maintenance, if the remaining time is more than 5 days, change the end time to 5 days later
            maintenance_record = collection_maintenance_pump.find_one({"pump_type": pump_type})
            if maintenance_record['end_time'] - datetime.now() > timedelta(days=5):
                collection_maintenance_pump.update_one(
                    {"_id": maintenance_record['_id']},
                    {"$set": {"end_time": datetime.now() + timedelta(days=PUMP_MALFUNCTION_ALERT_DAYS)}}
                )
        
                add_alert(f"{pump_type} Pump Malfunction (Check in 5 Days)",
                    f"Deviation from nominal value for 2 consecutive cycles: {recent_sessions['spray_deviation'].iloc[0]} and {recent_sessions['spray_deviation'].iloc[1]}")
            
            # in case there are less than 5 days remaining for maintenance, check if there is already an alert added whithin last 24 hours for maintenance in order to prevent spamming
            else:
                last_alert = collection_alerts.find_one({"message": f"{pump_type} Pump Malfunction (Check in 5 Days)"})
                if not last_alert:
                    add_alert(f"{pump_type} Pump Malfunction (Check in 5 Days)",
                        f"Deviation from nominal value for 2 consecutive cycles: {recent_sessions['spray_deviation'].iloc[0]} and {recent_sessions['spray_deviation'].iloc[1]}")
                elif datetime.now() - last_alert['time'] > timedelta(days=DAYS_BETWEEN_SAME_ALERTS):
                    add_alert(f"{pump_type} Pump Malfunction (Check in 5 Days)",
                        f"Deviation from nominal value for 2 consecutive cycles: {recent_sessions['spray_deviation'].iloc[0]} and {recent_sessions['spray_deviation'].iloc[1]}")
    except LookupError as e:
        pass
    pass

def estimate_filter_life(pump_type, nominal_value_speed, maintenance_record_start_date):
    """
    Estimates the remaining filter life based on pump type, nominal value speed, and maintenance record start date.

    Args:
        pump_type (str): The type of pump.
        nominal_value_speed (float): The nominal value speed of the pump.
        maintenance_record_start_date (str): The start date of the maintenance record in the format 'YYYY-MM-DD HH:MM:SS AM/PM'.

    Returns:
        float: The estimated remaining filter life in days.
    """
     
    # get all sessions after the start date
    recent_sessions = []

    all_sessions = list(collection_sessions.find({
        # "start_time": {"$gte": start_day, "$lte": end_day}
    }, {}).sort('id', -1))
    
    for session in all_sessions:
        # if the session is before the maintenance_record_start_date, we break the loop
        if datetime.strptime(session['start_time'], '%Y-%m-%d %I:%M:%S %p') < maintenance_record_start_date:
            break
        else:
            recent_sessions.append(session)

    recent_sessions = pd.DataFrame(recent_sessions)

    ### if the number of the sessions are lower than 20, we can't estimate the filter life using ML accurately, and we resort to simple calculations
    if len(recent_sessions) < 2:
        days_remaining_filter_estimate = DEFAUL_MAINTEANCE_FILTER 
    elif len(recent_sessions) < 20:
        deviation_speed = (recent_sessions['avg_speed'].mean() - nominal_value_speed) / nominal_value_speed
        days_remaining_filter_estimate = DEFAUL_MAINTEANCE_FILTER - DEFAUL_MAINTEANCE_FILTER * deviation_speed / 0.15
    else:
        # here we try to use scikit-learn to fit a Support Vector Regressor model to the speed data
        days_past_from_filter_change = (datetime.now() - maintenance_record_start_date).days
        average_run_per_day = len(recent_sessions) / days_past_from_filter_change
        X = recent_sessions['avg_speed'].values.reshape(-1, 1)
        y = np.array(recent_sessions.index)
        model = SVR(kernel='linear')
        model.fit(X, y)
        target_speed = 0.85 * nominal_value_speed
        estimated_run_index = model.predict([[target_speed]])
        predicted_session_date = estimated_run_index[0] / average_run_per_day
        days_remaining_filter_estimate = predicted_session_date - days_past_from_filter_change
        
        if days_remaining_filter_estimate < 0:
            # The model has failed to properly estimate the filter life, we resort to simple calculations
            deviation_speed = (recent_sessions['avg_speed'].mean() - nominal_value_speed) / nominal_value_speed
            days_remaining_filter_estimate = DEFAUL_MAINTEANCE_FILTER - DEFAUL_MAINTEANCE_FILTER * deviation_speed / 0.15
        pass
    return days_remaining_filter_estimate
    

def check_filter_life(pump_type):
    """
    Checks the filter life for a given pump type and performs necessary actions based on the filter life.

    Args:
        pump_type (str): The type of pump. It should be either "gelcoat" or "barrier".

    Returns:
        bool: True if the filter life is checked successfully, False otherwise.
    """
    try:
        maintenance_record = collection_maintenance_filter.find_one({"pump_type": pump_type})
        maintenance_record_start_date = datetime.strptime(maintenance_record['start_time'], '%Y-%m-%d %I:%M:%S %p')

        if datetime.now() - maintenance_record_start_date < timedelta(days=1):
            return True

        if pump_type == "gelcoat":
            nominal_value_speed = get_nominal_value_speed_gelcoat()
        elif pump_type == "barrier":
            nominal_value_speed = get_nominal_value_speed_barrier()
        else:
            raise ValueError(
                f"Invalid pump type, it should be either gelcoat or barrier. '{pump_type}' is given.")

        if collection_sessions.count_documents({}) % DELAY_FILTER_LIFE == 0:
            remaining_days = estimate_filter_life(pump_type, nominal_value_speed, maintenance_record_start_date)
            maintenance_record = collection_maintenance_filter.find_one({"pump_type": pump_type})
            collection_maintenance_filter.update_one(
                {"_id": maintenance_record['_id']},
                {"$set": {"end_time": datetime.now() + timedelta(days=remaining_days)}}
            )

            if remaining_days < 5:
                last_alert = collection_alerts.find_one({"message": f"{pump_type} Filter Life less than 5 days"})
                if not last_alert:
                    add_alert(f"{pump_type} Filter Life less than 5 days",
                        f"Remaining days for filter life: {remaining_days}")
                elif datetime.now() - last_alert['time'] > timedelta(days=DAYS_BETWEEN_SAME_ALERTS):
                    add_alert(f"{pump_type} Filter Life less than 5 days",
                        f"Remaining days for filter life: {remaining_days}")

    except LookupError as e:
        pass        
    pass


if __name__ == '__main__':

    add_first_maintenance_recored()
    current_cycle_gelcoat = pd.DataFrame(columns=ALL_COLUMNS)
    current_cycle_barrier = pd.DataFrame(columns=ALL_COLUMNS)
    
    # as it starts, send a request to the api to get new_sessions
    time.sleep(3)
    print("Sending a request to the API to get new sessions", file=sys.stderr)
    logging.debug("Sending a request to the API to get new sessions")
    requests.get("http://api:5000/api/get_new_sessions")
    logging.debug("Request sent to get new sessions")
    print("Request sent", file=sys.stderr)

    while True:
        
        time.sleep(DELAY)
        # get the latest document from the sensor data collection
        latest_data = pd.DataFrame(collection_sensor_data.find({}, sort=[("_id", -1)]).limit(int(DELAY * PER_SECONDS_READS)))
        latest_data = latest_data[::-1].reset_index(drop=True)

        # check whether gelcoat and barrier are on

        if not latest_data[-1*ZEROS_THRESHOLD:].Gelcoat_pulses.sum() + latest_data[:ZEROS_THRESHOLD].Gelcoat_pulses.sum() + latest_data[-1*ZEROS_THRESHOLD:].Barr_pulses.sum() + latest_data[:ZEROS_THRESHOLD].Barr_pulses.sum():
            # It's OFF
            print("It's OFF", file=sys.stderr)
            logging.info("It's OFF")

            # Check Whether the cycles are empty or not
            if not current_cycle_gelcoat.empty:
                # add_cycle_record_to_db(current_cycle_gelcoat, "gelcoat")
                # check PUMP MALFUNCTION function
                check_pump_malfunction("gelcoat")
                # check FILTER LIFE function
                check_filter_life("gelcoat")
                # Empty the cycle
                current_cycle_gelcoat = pd.DataFrame(columns=ALL_COLUMNS)
                pass

            elif not current_cycle_barrier.empty:
                # add_cycle_record_to_db(current_cycle_barrier, "barrier")
                # check PUMP MALFUNCTION function
                check_pump_malfunction("barrier")
                # check FILTER LIFE function
                check_filter_life("barrier")
                # Empty the cycle
                current_cycle_barrier = pd.DataFrame(columns=ALL_COLUMNS)
                pass
            
            
            # if it was after 6 pm, once per day, send a request to the delete_useless_reads_from_db endpoint to do some cleaning
            if datetime.now().hour >= 18:
                # last time the request was sent can be obtained from collection_delete_useless_reads
                last_request_time = collection_delete_useless_reads.find_one()["time"]
                
                if datetime.now() - last_request_time > timedelta(days=1):
                    logging.debug("Sending a request to the API to delete useless reads")
                    requests.get("http://api:5000/api/delete_useless_reads_from_db")
                    logging.debug("Request sent to delete useless reads")
                
            
            continue
        
        elif latest_data[-1*ZEROS_THRESHOLD:].Barr_pulses.sum() > 0 and latest_data[:ZEROS_THRESHOLD].Barr_pulses.sum() == 0:
            # Barrier was off but its on now
            print("Barrier was off but its on now", file=sys.stderr)
            logging.info("Barrier was off but its on now")
            # check for the first nonzero index
            first_non_zero_value_idx = latest_data[latest_data.Barr_pulses > 0].index[0]
            latest_data_ = latest_data.loc[first_non_zero_value_idx:]
            # Adding the nonzero part to the current cycle
            
            if len(current_cycle_barrier):
                current_cycle_barrier = pd.concat([current_cycle_barrier, deepcopy(latest_data_)]).reset_index(drop=True)
            else:
                current_cycle_barrier = deepcopy(latest_data_)
            
                
            if len(current_cycle_gelcoat):
                # Gelcoat is turned off but it was on
                print("Gelcoat is turned off but it was on", file=sys.stderr)
                logging.info("Gelcoat is turned off but it was on")
                last_non_zero_value_idx = latest_data[latest_data.Gelcoat_pulses > 0].index[-1]
                latest_data = latest_data.loc[:last_non_zero_value_idx]
                current_cycle_gelcoat = pd.concat([current_cycle_gelcoat, deepcopy(latest_data)]).reset_index(drop=True)
                # check PUMP MALFUNCTION function
                check_pump_malfunction("gelcoat")
                # check FILTER LIFE function
                check_filter_life("gelcoat")
                current_cycle_gelcoat = pd.DataFrame(columns=ALL_COLUMNS)
                    
                    
        elif latest_data[-1*ZEROS_THRESHOLD:].Gelcoat_pulses.sum() > 0 and latest_data[:ZEROS_THRESHOLD].Gelcoat_pulses.sum() == 0:
            # Gelcoat was off but its on now
            print("Gelcoat was off but its on now", file=sys.stderr)
            logging.info("Gelcoat was off but its on now")
            # check for the first nonzero index
            first_non_zero_value_idx = latest_data[latest_data.Gelcoat_pulses > 0].index[0]
            latest_data_ = latest_data.loc[first_non_zero_value_idx:]
            # Adding the nonzero part to the current cycle

            if len(current_cycle_gelcoat):
                current_cycle_gelcoat = pd.concat([current_cycle_gelcoat, deepcopy(latest_data_)]).reset_index(drop=True)
            else:
                current_cycle_gelcoat = deepcopy(latest_data_)
                
            if len(current_cycle_barrier):
                #barrier is turned off but it was on
                print("Barrier is turned off but it was on", file=sys.stderr)
                logging.info("Barrier is turned off but it was on")
                last_non_zero_value_idx = latest_data[latest_data.Barr_pulses > 0].index[-1]
                latest_data = latest_data.loc[:last_non_zero_value_idx]
                current_cycle_barrier = pd.concat([current_cycle_barrier, deepcopy(latest_data)]).reset_index(drop=True)
                # check PUMP MALFUNCTION function
                check_pump_malfunction("barrier")
                # check FILTER LIFE function
                check_filter_life("barrier")
                current_cycle_barrier = pd.DataFrame(columns=ALL_COLUMNS)

        elif latest_data[-1*ZEROS_THRESHOLD:].Gelcoat_pulses.sum() == 0 and latest_data[:ZEROS_THRESHOLD].Gelcoat_pulses.sum() > 0:
            # Gelcoat was on but it turned off
            print("Gelcoat was on but it turned off", file=sys.stderr)
            logging.info("Gelcoat was on but it turned off")

            # Seperate nonzero parts
            last_non_zero_value_idx = latest_data[latest_data.Gelcoat_pulses > 0].index[-1]
            latest_data = latest_data.loc[:last_non_zero_value_idx]
            # Adding the nonzero part to the current cycle
            
            if len(current_cycle_gelcoat):
                current_cycle_gelcoat = pd.concat([current_cycle_gelcoat, deepcopy(latest_data)]).reset_index(drop=True)
            else:
                current_cycle_gelcoat = deepcopy(latest_data)

            # add_cycle_record_to_db(current_cycle_gelcoat, "gelcoat")
            # check PUMP MALFUNCTION function
            check_pump_malfunction("gelcoat")

            # check FILTER LIFE function
            check_filter_life("gelcoat")
            
            
            # Empty the current cycle
            current_cycle_gelcoat = pd.DataFrame(columns=ALL_COLUMNS)
            pass
        elif latest_data[-1*ZEROS_THRESHOLD:].Barr_pulses.sum() == 0 and latest_data[:ZEROS_THRESHOLD].Barr_pulses.sum() > 0:
            # Barrier was on but it turned off
            print("Barrier was on but it turned off", file=sys.stderr)
            logging.info("Barrier was on but it turned off")

            # Seperate nonzero parts
            last_non_zero_value_idx = latest_data[latest_data.Barr_pulses > 0].index[-1]
            latest_data = latest_data.loc[:last_non_zero_value_idx]
            # Adding the nonzero part to the current cycle
            if len(current_cycle_barrier):
                current_cycle_barrier = pd.concat([current_cycle_barrier, deepcopy(latest_data)]).reset_index(drop=True)
            else:
                current_cycle_barrier = deepcopy(latest_data)

            # add_cycle_record_to_db(current_cycle_barrier, "barrier")
            # check PUMP MALFUNCTION function
            check_pump_malfunction("barrier")

            # check FILTER LIFE function
            check_filter_life("barrier")
            
            # Empty the current cycle
            current_cycle_barrier = pd.DataFrame(columns=ALL_COLUMNS)

            pass
        elif latest_data[-1*ZEROS_THRESHOLD:].Gelcoat_pulses.sum() > 0 and latest_data[:ZEROS_THRESHOLD].Gelcoat_pulses.sum() > 0:
            # Gelcoat is on
            print("Gelcoat is on", file=sys.stderr)
            logging.info("Gelcoat is on")

            if len(current_cycle_gelcoat):
                current_cycle_gelcoat = pd.concat([current_cycle_gelcoat, deepcopy(latest_data)]).reset_index(drop=True)
            else:
                current_cycle_gelcoat = deepcopy(latest_data)

            # check BLOCKAGE
            check_blockage("gelcoat", current_cycle_gelcoat, latest_data)

            # check PRESSURE

            check_pressure(latest_data, "gelcoat")

            pass
        elif latest_data[-1*ZEROS_THRESHOLD:].Barr_pulses.sum() > 0 and latest_data[:ZEROS_THRESHOLD].Barr_pulses.sum() > 0:
            # Barrier is on
            print("Barrier is on", file=sys.stderr)
            logging.info("Barrier is on")
            
            if len(current_cycle_barrier):
                current_cycle_barrier = pd.concat([current_cycle_barrier, deepcopy(latest_data)]).reset_index(drop=True)
            else:
                current_cycle_barrier = deepcopy(latest_data)
            # check BLOCKAGE
            check_blockage("barrier", current_cycle_barrier, latest_data)

            # check PRESSURE
            check_pressure(latest_data, "barrier")

            pass
        


        
        
