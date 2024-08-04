from __future__ import print_function
from flask import Flask, jsonify, request
from pymongo import MongoClient
from flask_cors import CORS
from copy import deepcopy
from datetime import datetime
from datetime import timedelta
import os.path
import sys
import pandas as pd
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %I:%M:%S %p",
    filename="api_logs.log",
)

# 2024-04-07 11:00:00 AM
DEFAUL_MAINTEANCE_PUMP = 45
DEFAUL_MAINTEANCE_FILTER = 21

MIN_LENGTH_SESSION = 15  # Seconds
IS_GET_NEW_SESSIONS_RUNNING = 0
IS_DELETE_USELESS_READS_RUNNING = 0
IS_UPDATE_PRODUCT_DB_RUNNING = 0
IS_ADD_NEW_NOMINAL_SESSION_RUNNING = 0

PER_SECONDS_READS = 10

num_datapoints_sent = 5 * PER_SECONDS_READS
app = Flask(__name__)
CORS(app)

client = MongoClient("mongodb://db:27017")

try:
    _ = client.server_info()
except:
    print("*"*100)
    print("FLASK API CANNOT CONNECT TO MONGODB")
    print("*"*100)
    logging.critical("FLASK API CANNOT CONNECT TO MONGODB")


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
#! IN PANOS's CODE THERE ARE NO SEPERATE VALUES OF WEIGHT_PER_PULSE FOR GELCOAT AND BARRIER
WEIGHT_PER_PULSE_GELCOAT = PUMP_VOLUME / \
    PULSE_PER_FULL_STROKE * GELCOAT_SPEC_WEIGHT / 100
WEIGHT_PER_PULSE_BARRIER = PUMP_VOLUME / \
    PULSE_PER_FULL_STROKE * GELCOAT_SPEC_WEIGHT / 100

COLUMNS_WEIGHT_PER_PULSE = {
    "gelcoat": WEIGHT_PER_PULSE_GELCOAT,
    "barrier": WEIGHT_PER_PULSE_BARRIER
}

db = client["Sensor_Data"]
collection = db["test_28_march"]

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


@app.route('/api/get_20', methods=['GET'])
def get_20():
    """
    Retrieves the latest num_datapoints_sent data points from the collection and calculates various metrics.

    Returns:
        A JSON response containing the following information:
        - data: A list of the latest num_datapoints_sent data points retrieved from the collection.
        - total_weight_barr: The total weight of barrier pulses calculated based on the sum of 'Barr_pulses' field in the data.
        - total_weight_gel: The total weight of gelcoat pulses calculated based on the sum of 'Gelcoat_pulses' field in the data.
        - pressure: The average pressure calculated based on the 'Pressure' field in the data.

    Raises:
        Exception: If an error occurs while retrieving the data or calculating the metrics.
    """
    
    global num_datapoints_sent
    try:
        data_20 = list(collection.find({}, {
            '_id': 0,
            'time': 1,
            'Barr_pulses': 1,
            'Gelcoat_pulses': 1,
            'Barrier_speedRPM': 1,
            'Gelcoat_speedRPM': 1,
            'WaterLevel_1': 1,
            'WaterLevel_2': 1,
            'Pressure': 1
        }).sort('_id', -1).limit(num_datapoints_sent)) 
        
        data = pd.DataFrame(data_20)
        barr_pulses = data['Barr_pulses'].sum()
        gelcoat_pulses = data['Gelcoat_pulses'].sum()
        weight_per_pulse_barr = COLUMNS_WEIGHT_PER_PULSE["barrier"]
        weight_per_pulse_gel = COLUMNS_WEIGHT_PER_PULSE["gelcoat"]
        avg_pressure = data["Pressure"].mean()
        total_weight_barr = barr_pulses * weight_per_pulse_barr
        total_weight_gel = gelcoat_pulses * weight_per_pulse_gel
        response = {
            "data": data_20,
            "total_weight_barr": int(total_weight_barr),
            "total_weight_gel": int(total_weight_gel),
            "pressure": avg_pressure
        }
        return jsonify(response), 200
    except Exception as e:
        logging.error(f"get_20 < Exception: {str(e)} >")
        return jsonify({"error get_20": str(e)}), 500


def binary_search_history(all_sessions, start_date, end_date):
    """
    Performs binary search on a list of sessions to find the index of a session that falls within a given date range.

    Args:
        all_sessions (list): A list of sessions, where each session is a dictionary containing "start_time" and "end_time" keys.
        start_date (datetime): The start date of the desired date range.
        end_date (datetime): The end date of the desired date range.

    Returns:
        int: The index of the session that falls within the given date range. Returns -1 if no session is found.

    Raises:
        ValueError: If the start_date is greater than the end_date.
    """
    
    left_cursor = 0
    right_cursor = len(all_sessions) - 1
    
    while left_cursor <= right_cursor:

        mid = left_cursor + (right_cursor - left_cursor) // 2
        session_end_time = datetime.strptime(all_sessions[mid]["end_time"], '%Y-%m-%d %I:%M:%S %p')
        session_start_time = datetime.strptime(all_sessions[mid]["start_time"], '%Y-%m-%d %I:%M:%S %p')
        
        if session_end_time >= start_date and session_start_time <= end_date:
            # Check if x is present at mid
            return mid
        elif session_end_time < start_date:
            # we should go right, ignore left half
            left_cursor = mid + 1
        else:
            # we should go left, ignore right half
            right_cursor = mid - 1
    # If we reach here, then the element was not present
    return -1


@app.route('/api/history', methods=['POST'])
def get_history():
    """
    Retrieves the history of sessions between a given start date and end date.
    
    Returns:
        A JSON response containing the list of sessions within the specified date range.
        
    Raises:
        Exception: If an error occurs during the retrieval process.
    """
    try:
        data = request.get_json()
        start_date = datetime.strptime(data['startDate'], '%Y-%m-%d %I:%M:%S %p')
        end_date = datetime.strptime(data['endDate'], '%Y-%m-%d %I:%M:%S %p')
        
        # if start_date is greater than end_date, we swap them
        if start_date > end_date:
            start_date, end_date = end_date, start_date
        
        # find all sessions between the start_date and end_date
        sessions_to_show = []

        all_sessions = list(collection_sessions.find({}).sort('_id', 1))
        
        ### The sessions are sorted by their _id which is equivalent to their start_time and id
        ### first, we try to find a sessions that has an end_time greater than the start_date and a start_time less than the end_date
        ### We want to find this session in log(n) time
        
        session_mid_index = binary_search_history(all_sessions, start_date, end_date)
        
        if session_mid_index == -1:
            return jsonify([]), 200
        else:
            # we found the session, now we need to find the first session that has an end_time greater than the start_date
            # and a start_time less than the end_date
            left_cursor = session_mid_index
            right_cursor = session_mid_index
            while left_cursor >= 0 and datetime.strptime(all_sessions[left_cursor]["end_time"], '%Y-%m-%d %I:%M:%S %p') >= start_date:
                left_cursor -= 1
            while right_cursor < len(all_sessions) and datetime.strptime(all_sessions[right_cursor]["start_time"], '%Y-%m-%d %I:%M:%S %p') <= end_date:
                right_cursor += 1
            
            sessions_to_show = all_sessions[left_cursor+1:right_cursor]
        
        if not sessions_to_show:
            return jsonify([]), 200
        
        if datetime.strptime(sessions_to_show[0]["start_time"], '%Y-%m-%d %I:%M:%S %p') > start_date:
            id_start = collection.find_one({"time": sessions_to_show[0]["start_time"]})["_id"]
        else:
            id_start = collection.find_one({"time": data['startDate']} )["_id"]
            
        if datetime.strptime(sessions_to_show[-1]["end_time"], '%Y-%m-%d %I:%M:%S %p') < end_date:
            id_end = collection.find_one({"time": sessions_to_show[-1]["end_time"]}, sort=[('_id', -1)])["_id"]
        else:
            id_end = collection.find_one({"time": data['endDate']})["_id"]
        
        results = collection.find({
            '_id': {
                '$gte': id_start, 
                '$lte': id_end
                }
            }, {'_id': 0,}, sort=[('_id', 1)])
        results_list = list(results)
        logging.info(f"History tab < input_startDate: {start_date}, input_endDate: {end_date}, id_start: {id_start}, id_end: {id_end}, start_time: {results_list[0]['time']}, end_time: {results_list[-1]['time']} ,len_sessions: {len(sessions_to_show)} >")
        
        return jsonify(results_list), 200
    except Exception as e:
        logging.error(f"History tab < Exception: {str(e)}, input_startDate: {start_date}, input_endDate: {end_date} >")
        return jsonify({"error get_history": str(e)}), 500


@app.route('/api/get_starts_gelcoat', methods=['GET'])
def get_starts_gelcoat(since=None):
    """
    Retrieves the start and end times of gelcoat sessions from a database collection.
    
    Args:
        since (optional): The "_id" of the last seen record in the database. Defaults to None.
    
    Returns:
        tuple: A tuple containing the gelcoat session information in the following format:
            - begin (str): The start time of the session.
            - end (str): The end time of the session.
            - pump_type (str): The type of pump used during the session (always 'gelcoat').
            - length (float): The duration of the session in seconds.
    
    Raises:
        Exception: If an error occurs while retrieving the gelcoat session information.
    """
    try:
        starts_gel = []
        ends_gel = []

        if since is None:
            # retrieve non-zero values
            data = list(collection.find({'Gelcoat_speedRPM': {'$gt': 0}}, {
                '_id': 0,
                'time': 1,
            }).sort('_id', 1))
        else:
            # since is the "_id" of the last seen record in the database
            data = list(collection.find({'_id': {'$gt': since}, 'Gelcoat_speedRPM': {'$gt': 0}}, {
                '_id': 0,
                'time': 1,
            }).sort('_id', 1))
            

        if not data:
            return jsonify([]), 200
        
        for i in range(len(data) - 1):
            if i == 0:
                starts_gel.append(data[i]['time'])
            # converting to datetime object
            curr_time = datetime.strptime(
                data[i]['time'], '%Y-%m-%d %I:%M:%S %p')
            next_time = datetime.strptime(
                data[i+1]['time'], '%Y-%m-%d %I:%M:%S %p')
            # we allow for having MIN_LENGTH_SESSION consecutive zero values within a session
            if (next_time - curr_time).total_seconds() > MIN_LENGTH_SESSION:
                starts_gel.append(data[i+1]['time'])
                ends_gel.append(data[i]['time'])
        ends_gel.append(data[-1]['time'])

        # removing session shorter than MIN_LENGTH_SESSION seconds
        final_starts_gel = []
        final_ends_gel = []
        for i in range(len(starts_gel)):
            if (datetime.strptime(ends_gel[i], '%Y-%m-%d %I:%M:%S %p') - datetime.strptime(starts_gel[i], '%Y-%m-%d %I:%M:%S %p')).total_seconds() > MIN_LENGTH_SESSION:
                final_starts_gel.append(starts_gel[i])
                final_ends_gel.append(ends_gel[i])

        # creating response object
        output = [{"begin": start, "end": end, 'pump_type': 'gelcoat', "length": (datetime.strptime(end, '%Y-%m-%d %I:%M:%S %p') - datetime.strptime(start, '%Y-%m-%d %I:%M:%S %p')).total_seconds()}
                  for start, end in zip(final_starts_gel, final_ends_gel)]

        logging.info(f"get_starts_gelcoat < since: {since} >")
        return jsonify(output), 200
    except Exception as e:
        logging.error(f"get_starts_gelcoat < Exception: {str(e)}, since: {since} >")
        return jsonify({"error get_starts_gelcoat": str(e)}), 500


@app.route('/api/get_starts_barrier', methods=['GET'])
def get_starts_barrier(since=None):
    """
    Retrieves the start and end times of barrier sessions from a database collection.
    
    Args:
        since (optional): The "_id" of the last seen record in the database. Defaults to None.
    
    Returns:
        tuple: A tuple containing the gelcoat session information in the following format:
            - begin (str): The start time of the session.
            - end (str): The end time of the session.
            - pump_type (str): The type of pump used during the session (always 'gelcoat').
            - length (float): The duration of the session in seconds.
    
    Raises:
        Exception: If an error occurs while retrieving the gelcoat session information.
    """
    
    try:
        starts_bar = []
        ends_bar = []

        if since is None:
            # retrieve non-zero values
            data = list(collection.find({'Barrier_speedRPM': {'$gt': 0}}, {
                '_id': 0,
                'time': 1,
            }).sort('_id', 1))
        else:
            # since is the "_id" of the last seen record in the database
            data = list(collection.find({'_id': {'$gt': since}, 'Barrier_speedRPM': {'$gt': 0}}, {
                '_id': 0,
                'time': 1,
            }).sort('_id', 1))

        if not data:
            return jsonify([]), 200
            

        for i in range(len(data) - 1):
            if i == 0:
                starts_bar.append(data[i]['time'])
            # converting to datetime object
            curr_time = datetime.strptime(
                data[i]['time'], '%Y-%m-%d %I:%M:%S %p')
            next_time = datetime.strptime(
                data[i+1]['time'], '%Y-%m-%d %I:%M:%S %p')
            # we allow for having MIN_LENGTH_SESSION consecutive zero values within a session
            if (next_time - curr_time).total_seconds() > MIN_LENGTH_SESSION:
                starts_bar.append(data[i+1]['time'])
                ends_bar.append(data[i]['time'])
        ends_bar.append(data[-1]['time'])
            
        # removing session shorter than MIN_LENGTH_SESSION seconds
        final_starts_bar = []
        final_ends_bar = []
        for i in range(len(starts_bar)):
            if (datetime.strptime(ends_bar[i], '%Y-%m-%d %I:%M:%S %p') - datetime.strptime(starts_bar[i], '%Y-%m-%d %I:%M:%S %p')).total_seconds() > (MIN_LENGTH_SESSION):
                final_starts_bar.append(starts_bar[i])
                final_ends_bar.append(ends_bar[i])
        output = [{"begin": start, "end": end, "pump_type": "barrier", "length": (datetime.strptime(end, '%Y-%m-%d %I:%M:%S %p') - datetime.strptime(start, '%Y-%m-%d %I:%M:%S %p')).total_seconds()}
                  for start, end in zip(final_starts_bar, final_ends_bar)]
        logging.info(f"get_starts_barrier < since: {since} >")
        return jsonify(output), 200
    except Exception as e:
        logging.error(f"get_starts_barrier < Exception: {str(e)}, since: {since} >")
        return jsonify({"error get_starts_barrier": str(e)}), 500


@app.route('/api/get_starts_gelcoat_and_barrier', methods=['GET'])
def get_starts_gelcoat_and_barrier(since=None):
    """
    Retrieves the starts of gelcoat and barrier sessions and merges them into a single list.
    
    Args:
        since (optional): The starting _id to filter the sessions. Defaults to None.
        
    Returns:
        tuple: A tuple containing the merged list of sessions and the HTTP status code.
        
    Raises:
        Exception: If an error occurs while retrieving the sessions.
    """
    try:
        starts_gelcoat = get_starts_gelcoat(since)[0].json
        starts_barrier = get_starts_barrier(since)[0].json
        
        ### these two lists are sorted by the begin time
        ### now we need to merge them and the final list should also be sorted by the begin time
        ### peform this merge in most eficient way (O(n))
        all_sessions = []
        i = 0
        j = 0
        while i < len(starts_gelcoat) and j < len(starts_barrier):
            if datetime.strptime(starts_gelcoat[i]['begin'], '%Y-%m-%d %I:%M:%S %p') < datetime.strptime(starts_barrier[j]['begin'], '%Y-%m-%d %I:%M:%S %p'):
                all_sessions.append(starts_gelcoat[i])
                i += 1
            else:
                all_sessions.append(starts_barrier[j])
                j += 1

        # Add remaining elements from starts_gelcoat, if any
        while i < len(starts_gelcoat):
            all_sessions.append(starts_gelcoat[i])
            i += 1
    
        # Add remaining elements from starts_barrier, if any
        while j < len(starts_barrier):
            all_sessions.append(starts_barrier[j])
            j += 1
            
        
        logging.info(f"get_starts_gelcoat_and_barrier < since: {since} >")
        return jsonify(all_sessions), 200
    except Exception as e:
        logging.error(f"get_starts_gelcoat_and_barrier < Exception: {str(e)}, since: {since} >")
        return jsonify({"error get_starts_gelcoat_and_barrier": str(e)}), 500

@app.route('/api/delete_useless_reads_from_db', methods=['GET'])
def delete_useless_reads_from_db():
    """
    Deletes useless sensor reads from the database based on certain criteria.

    This function deletes sensor reads from the database that are considered useless. The criteria for determining useless reads are as follows:
    1. If it is the first time running this function, all sensor reads that are sooner than the first session are deleted.
    2. For subsequent runs, all reads between the end of a session and the start of the next session are deleted, except for the last 4 sessions.
    3. If there is a time overlap between two sessions, the data between them is not deleted.
    4. If the current time period is within the previous time periods, the data is deleted differently.
    5. Only reads with almost zero barrier speed and gelcoat speed are deleted.

    Returns:
        A JSON response indicating the status of the operation.
    """
    global IS_DELETE_USELESS_READS_RUNNING
    try:
        if not IS_DELETE_USELESS_READS_RUNNING:
            IS_DELETE_USELESS_READS_RUNNING = 1
            # check whether it is the first time we run this function, checking the length of the collection_delete_useless_reads
            if collection_delete_useless_reads.count_documents({}) == 0:
                # Check from the beginning of the database
                since = None
                all_sessions = get_starts_gelcoat_and_barrier()[0].json
                
                # delete all sensor reads that are sooner than the first session (we use _id in order to find earlier reads)
                collection.delete_many({
                    "_id": {"$lt": collection.find_one({"time": all_sessions[0]["begin"]})["_id"]}
                })
                
            else:
                since = collection_delete_useless_reads.find_one({})["since"]
                all_sessions = get_starts_gelcoat_and_barrier(since)[0].json

            # We delete all reads that are between the end of a session and the start of the next session
            # we do this for all sessions except the last 4 sessions, in order to avoid deleting the data between the last session and the current time which is important for the agent
            for i in range(len(all_sessions) - 4):
                # check whether these session have time overlap
                if datetime.strptime(all_sessions[i]["end"], '%Y-%m-%d %I:%M:%S %p') >= datetime.strptime(all_sessions[i+1]["begin"], '%Y-%m-%d %I:%M:%S %p'):
                    # if they have overlap, we skip deleting data between them
                    continue

                # if the current time period is within the previous time periods, we delete the data differently
                if datetime.strptime(all_sessions[i]["end"], '%Y-%m-%d %I:%M:%S %p') <= datetime.strptime(all_sessions[i-1]["end"], '%Y-%m-%d %I:%M:%S %p'):
                    latest_previous_end = datetime.strptime(
                        all_sessions[i-1]["end"], '%Y-%m-%d %I:%M:%S %p')
                    j = 2
                    while latest_previous_end <= datetime.strptime(all_sessions[i-j]["end"], '%Y-%m-%d %I:%M:%S %p'):
                        latest_previous_end = datetime.strptime(
                            all_sessions[i-j]["end"], '%Y-%m-%d %I:%M:%S %p')
                        j += 1
                        
                    if latest_previous_end < datetime.strptime(all_sessions[i+1]["begin"], '%Y-%m-%d %I:%M:%S %p'):
                        collection.delete_many({
                            "_id": {
                                "$gt": collection.find_one({"time": all_sessions[i-j+1]["end"]}, sort=[('_id', -1)])["_id"],
                                "$lt": collection.find_one({"time": all_sessions[i+1]["begin"]})["_id"]
                            },
                            # and they must also have almost zero barrier speed and gelcoat speed
                            "Barrier_speedRPM": {"$lt": 0.0001},
                            "Gelcoat_speedRPM": {"$lt": 0.0001}
                        })
                    continue

                collection.delete_many({
                    "_id": {
                        "$gt": collection.find_one({"time": all_sessions[i]["end"]}, sort=[('_id', -1)])["_id"],
                        "$lt": collection.find_one({"time": all_sessions[i+1]["begin"]})["_id"]
                    },
                    # and they must also have almost zero barrier speed and gelcoat speed
                    "Barrier_speedRPM": {"$lt": 0.0001},
                    "Gelcoat_speedRPM": {"$lt": 0.0001}
                })
                
            # update the since field in the collection_delete_useless_reads
            since_new = collection.find_one({"time": all_sessions[-4]["end"]})["_id"]
            collection_delete_useless_reads.delete_many({})
            collection_delete_useless_reads.insert_one({
                "since": since_new,
                "time": datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
            })
            
            IS_DELETE_USELESS_READS_RUNNING = 0
            logging.info(f"delete_useless_reads_from_db < since: {since}, since_new: {since_new} >")
            return jsonify("Done"), 200
        else:
            logging.info("delete_useless_reads_from_db < The delete useless reads is being calculated >")
            return jsonify("The delete useless reads is being calculated, please wait")
    except Exception as e:
        IS_DELETE_USELESS_READS_RUNNING = 0
        logging.error(f"delete_useless_reads_from_db < Exception: {str(e)}, since: {since} >")
        return jsonify({"error delete_useless_reads_from_db": str(e)}), 500

@app.route('/api/delete_all_session_from_collection', methods=['GET'])
def delete_all_session_from_collection():
    """
    Deletes all sessions from the sessions collection.

    Returns:
        A JSON response indicating the status of the operation.
    """
    try:
        collection_sessions.delete_many({})
        logging.warning("delete_all_session_from_collection < Done >")
        return jsonify("Done"), 200
    except Exception as e:
        logging.error(f"delete_all_session_from_collection < Exception: {str(e)} >")
        return jsonify({"error delete_all_session_from_collection": str(e)}), 500

def reset_all_valid_sessions_from_sensor_data():
    global IS_GET_NEW_SESSIONS_RUNNING
    """
    Resets all valid sessions from sensor data.

    This function retrieves a list of sessions from the sensor data, calculates various metrics for each session,
    and stores the session information in a separate collection. It also deletes unnecessary data from the sensor data collection.

    Returns:
        A JSON response containing the list of sessions and a status code.

    Raises:
        Exception: If an error occurs during the process.
    """
    try:
        # a list of dictionaries, each dictionary represents a session like this: {"begin": "2024-04-07 11:00:00 AM", "end": "2024-04-07 11:00:15 AM", "pump_type": "gelcoat", "length": 15}, indicationg sessions of gelcoat and barrier
        all_sessions = get_starts_gelcoat_and_barrier()[0].json

        try:
            collection.delete_many({
                "_id": {"$lt": collection.find_one({"time": all_sessions[0]["begin"]})["_id"]}
            })
        except:
            pass
        
        for i in range(len(all_sessions)):
            session = all_sessions[i]
            start_time_id = collection.find_one({
                "time": session["begin"]
            })["_id"]
            
            end_time_id = collection.find_one({
                "time": session["end"]
            }, sort=[('_id', -1)])["_id"]            
            
            # get the data between the start and end time
            session_data = pd.DataFrame(collection.find({
                "_id": {"$gte": start_time_id, "$lt": end_time_id}
            }))
            
            # calculate the total pulses
            column_name_pulse = COLUMNS_TO_CHECK_PULSES[session["pump_type"]]
            weight_per_pulse = COLUMNS_WEIGHT_PER_PULSE[session["pump_type"]]
            sum_pulses = session_data[column_name_pulse].sum()
            total_weight = sum_pulses * weight_per_pulse
            avg_pressure = session_data["Pressure"].mean()
            avg_speed = session_data[column_name_pulse].sum() / (datetime.strptime(session["end"], '%Y-%m-%d %I:%M:%S %p') - datetime.strptime(session["begin"], '%Y-%m-%d %I:%M:%S %p')).total_seconds()
            document = {
                "id": i+1,
                "start_time": session["begin"],
                "end_time": session["end"],
                "pump_type": session["pump_type"],
                "length": session["length"],
                "total_sprayed_amount": total_weight,
                "avg_speed": avg_speed,
                "avg_pressure":avg_pressure,
                "comments": "",
                "is_trash": 0,
            }
            collection_sessions.insert_one(document)
            
            if i < len(all_sessions) - 4:
                if datetime.strptime(all_sessions[i]["end"], '%Y-%m-%d %I:%M:%S %p') >= datetime.strptime(all_sessions[i+1]["begin"], '%Y-%m-%d %I:%M:%S %p'):
                    # if they have overlap, we skip deleting data between them
                    continue

                # if the current time period is within the previous time periods, we delete the data differently
                if datetime.strptime(all_sessions[i]["end"], '%Y-%m-%d %I:%M:%S %p') <= datetime.strptime(all_sessions[i-1]["end"], '%Y-%m-%d %I:%M:%S %p'):
                    latest_previous_end = datetime.strptime(
                        all_sessions[i-1]["end"], '%Y-%m-%d %I:%M:%S %p')
                    j = 2
                    while latest_previous_end <= datetime.strptime(all_sessions[i-j]["end"], '%Y-%m-%d %I:%M:%S %p'):
                        latest_previous_end = datetime.strptime(
                            all_sessions[i-j]["end"], '%Y-%m-%d %I:%M:%S %p')
                        j += 1
                        

                    if latest_previous_end < datetime.strptime(all_sessions[i+1]["begin"], '%Y-%m-%d %I:%M:%S %p'):
                        collection.delete_many({
                            "_id": {
                                "$gt": collection.find_one({"time": all_sessions[i-j+1]["end"]}, sort=[('_id', -1)])["_id"],
                                "$lt": collection.find_one({"time": all_sessions[i+1]["begin"]})["_id"]
                            },
                            # and they must also have almost zero barrier speed and gelcoat speed
                            "Barrier_speedRPM": {"$lt": 0.0001},
                            "Gelcoat_speedRPM": {"$lt": 0.0001}
                        })
                    continue

                collection.delete_many({
                    "_id": {
                        "$gt": collection.find_one({"time": all_sessions[i]["end"]}, sort=[('_id', -1)])["_id"],
                        "$lt": collection.find_one({"time": all_sessions[i+1]["begin"]})["_id"]
                    },
                    # and they must also have almost zero barrier speed and gelcoat speed
                    "Barrier_speedRPM": {"$lt": 0.0001},
                    "Gelcoat_speedRPM": {"$lt": 0.0001}
                })
                
        logging.info("reset_all_valid_sessions_from_sensor_data < Done >")
        IS_GET_NEW_SESSIONS_RUNNING = 0  
        return jsonify(all_sessions), 200
    except Exception as e:
        logging.error(f"reset_all_valid_sessions_from_sensor_data < Exception: {str(e)} >")
        return jsonify({"error reset_all_valid_sessions_from_sensor_data": str(e)}), 500


@app.route('/api/get_new_sessions', methods=['GET'])
def get_new_sessions():
    """
    Retrieves new sessions from the database and calculates session metrics.

    Returns:
        A JSON response containing the new sessions and their metrics.

    Raises:
        Exception: If an error occurs while retrieving or calculating the sessions.
    """
    global IS_GET_NEW_SESSIONS_RUNNING
    try:
        if not IS_GET_NEW_SESSIONS_RUNNING:
            # find the latest session in the database
            IS_GET_NEW_SESSIONS_RUNNING = 1
            latest_session = collection_sessions.find_one({}, sort=[('_id', -1)])

            # if the database is empty, we session the reset_all_valid_sessions_from_sensor_data function instead
            if latest_session is None:
                return reset_all_valid_sessions_from_sensor_data()
            # we find the sensor data associated with the end_time of the latest session
            latest_sensor_read = collection.find_one({
                "time": latest_session["end_time"]
                }, sort=[('_id', -1)])
            
            since = latest_sensor_read["_id"]
            
            new_sessions = get_starts_gelcoat_and_barrier(since)[0].json
            
            if not new_sessions:
                IS_GET_NEW_SESSIONS_RUNNING = 0  
                return jsonify([]), 200
            
            collection_size = collection_sessions.count_documents({})
            # add sessions to the database
            for i in range(len(new_sessions)):
                session = new_sessions[i]
                start_time_id = collection.find_one({
                    "time": session["begin"]
                })["_id"]
                
                end_time_id = collection.find_one({
                    "time": session["end"]
                }, sort=[('_id', -1)])["_id"]
                
                # get the data between the start and end time
                session_data = pd.DataFrame(collection.find({
                    "_id": {"$gte": start_time_id, "$lte": end_time_id}
                }))
                
                # calculate the total pulses
                column_name_pulse = COLUMNS_TO_CHECK_PULSES[session["pump_type"]]
                weight_per_pulse = COLUMNS_WEIGHT_PER_PULSE[session["pump_type"]]
                sum_pulses = session_data[column_name_pulse].sum()
                total_weight = sum_pulses * weight_per_pulse
                avg_pressure = session_data["Pressure"].mean()
                avg_speed = session_data[column_name_pulse].sum() / (datetime.strptime(session["end"], '%Y-%m-%d %I:%M:%S %p') - datetime.strptime(session["begin"], '%Y-%m-%d %I:%M:%S %p')).total_seconds()
                document = {
                    "id": i+1+collection_size,
                    "start_time": session["begin"],
                    "end_time": session["end"],
                    "pump_type": session["pump_type"],
                    "length": session["length"],
                    "total_sprayed_amount": total_weight,
                    "avg_speed": avg_speed,
                    "avg_pressure":avg_pressure,
                    "comments": "",
                    "is_trash": 0,
                }
                # print("DOCUMENT TO BE ADDED:", file=sys.stderr)
                logging.debug(f"get_new_sessions (Document to be added) < document: {document} >")
                collection_sessions.insert_one(document)
            IS_GET_NEW_SESSIONS_RUNNING = 0    
            logging.info(f"get_new_sessions < since: {since} >")
            return jsonify(new_sessions), 200
        else:
            logging.info("get_new_sessions < The new sessions are being calculated >")
            return jsonify("The new sessions are being calculated, please wait")
    except Exception as e:
        IS_GET_NEW_SESSIONS_RUNNING = 0
        logging.error(f"get_new_sessions < Exception: {str(e)} >")
        return jsonify({"error get_new_sessions": str(e)}), 500

@app.route('/api/get_all_sessions_from_collection', methods=['GET'])
def get_all_sessions_from_collection():
    """
    Retrieves all sessions from the collection.

    Returns:
        A tuple containing the JSON response and the HTTP status code.
        
    Raises:
        Exception: If an error occurs during the operation.
    """
    try:
        get_new_sessions()
        all_sessions = list(collection_sessions.find({"is_trash": 0}, {'_id': 0,}).sort('id', -1))
        logging.info("get_all_sessions_from_collection < Done >")
        return jsonify(all_sessions), 200
    except Exception as e:
        logging.error(f"get_all_sessions_from_collection < Exception: {str(e)} >")
        return jsonify({"error get_all_sessions_from_collection": str(e)}), 500

@app.route('/api/get_deleted_sessions_from_collection', methods=['GET'])
def get_deleted_sessions_from_collection():
    """
    Retrieves all deleted sessions from the collection.

    Returns:
        A tuple containing the JSON response and the HTTP status code.
        
    Raises:
        Exception: If an error occurs during the operation.
    """
    try:
        # find all sessions that their is_trash field is 1
        all_sessions = list(collection_sessions.find({"is_trash": 1}, {'_id': 0,}).sort('id', -1))
        logging.info("get_deleted_sessions_from_collection < Done >")
        return jsonify(all_sessions), 200
    except Exception as e:
        logging.error(f"get_deleted_sessions_from_collection < Exception: {str(e)} >")
        return jsonify({"error get_deleted_sessions_from_collection": str(e)}), 500


@app.route('/api/set_trash_by_id', methods=['POST'])
def set_trash_by_id():
    """
    Sets the 'is_trash' field to 1 for a document in the 'collection_sessions' collection based on the provided ID.

    Returns:
        A tuple containing the JSON response and the HTTP status code.
    Raises:
        Exception: If an error occurs during the operation.

    """
    data = request.get_json()
    try:
        collection_sessions.update_one({"id": int(data['id'])}, {
            "$set": {"is_trash": 1}
        })
        logging.info(f"set_trash_by_id < id: {data['id']} >")
        return jsonify("Done"), 200
    except Exception as e:
        try:
            logging.error(f"set_trash_by_id < Exception: {str(e)} , id: {request.get_json()['id']} >")
        except Exception as e2:
            logging.error(f"set_trash_by_id < Exception 1: {str(e)}, Exception 2: {str(e2)} >")
        return jsonify({"error set_trash_by_id": str(e)}), 500
    

@app.route('/api/restore_trash_session_by_id', methods=['POST'])
def restore_trash_session_by_id():
    """
    Restores a trashed session by its ID.

    This function takes a JSON payload containing the ID of the session to be restored.
    It updates the 'is_trash' field of the session document in the 'collection_sessions' collection to 0,
    indicating that the session is no longer in the trash.
    
    Returns:
            A tuple containing the JSON response and the HTTP status code.
        Raises:
            Exception: If an error occurs during the operation.
    """
    data = request.get_json()
    try:
        collection_sessions.update_one({"id": int(data['id'])}, {
            "$set": {"is_trash": 0}
        })
        logging.info(f"restore_trash_session_by_id < id: {data['id']} >")
        return jsonify("Done"), 200
    except Exception as e:
        try:
            logging.error(f"restore_trash_session_by_id < Exception: {str(e)} , id: {request.get_json()['id']} >")
        except Exception as e2:
            logging.error(f"restore_trash_session_by_id < Exception 1: {str(e)}, Exception 2: {str(e2)} >")
        return jsonify({"error": str(e)}), 500


@app.route('/api/set_comments_by_id_session', methods=['POST'])
def set_comments_by_id_session():
    """
    Updates the comments of a session with the given ID.

    This function receives a JSON payload containing the session ID and the new comment.
    It updates the comment field of the session with the corresponding ID in the database.

    Returns:
        A JSON response indicating the success of the operation.

    Raises:
        Exception: If an error occurs during the process.
    """
    
    data = request.get_json()
    try:
        collection_sessions.update_one({"id": int(data['id'])}, {
            "$set": {"comments": data['comments']}
        })
        logging.info(f"set_comments_by_id_session < id: {data['id']} >")
        return jsonify("Done"), 200
    except Exception as e:
        try:
            logging.error(f"set_comments_by_id_session < Exception: {str(e)} , id: {request.get_json()['id']} >")
        except Exception as e2:
            logging.error(f"set_comments_by_id_session < Exception 1: {str(e)}, Exception 2: {str(e2)} >")
        return jsonify({"error set_comments_by_id_session": str(e)}), 500


def get_all_products_from_sessions():
    """
    Retrieves all products from sessions.

    Returns:
        list: A list of products, where each product is a sequence of [gelcoat, gelcoat, barrier] sessions.
            Each product is represented as a string in the format 'start_time: <start_time>, end_time: <end_time>'.
            If an error occurs during the retrieval process, None is returned.
            
    Raises:
        Exception: If an error occurs during the process.
    """
    # a product is a sequence of [gelcoat, gelcoat, barrier] sessions
    try:
        all_sessions = list(collection_sessions.find({"is_trash": 0}).sort('_id', 1))
        products = []
        i = 0
        while i < len(all_sessions) - 2:
            if all_sessions[i]["pump_type"] == "gelcoat" and all_sessions[i+1]["pump_type"] == "gelcoat" and all_sessions[i+2]["pump_type"] == "barrier":
                gelcoat_material = all_sessions[i]["total_sprayed_amount"] + all_sessions[i+1]["total_sprayed_amount"]
                barrier_material = all_sessions[i+2]["total_sprayed_amount"]
                products.append(
                    f'start_time: {all_sessions[i]["start_time"]}, end_time: {all_sessions[i+2]["end_time"]}, gelcoat_material: {gelcoat_material}, barrier_material: {barrier_material}'
                )
                i += 3
            else:
                i += 1
        logging.info("get_all_products_from_sessions < Done >")
        return products
    except Exception as e:
        logging.error(f"get_all_products_from_sessions < Exception: {str(e)} >")
        return None


def update_product_db():
    """
    Updates the product database with the current products.

    This function retrieves all the current products from the sessions and updates the product database accordingly.
    If the product database is empty, it adds all the current products to the database.
    If the product database is not empty, it replaces all the existing products with the current products.
    If a current product already exists in the database, it keeps the comments and hide status of the existing product.

    Raises:
        Exception: If an error occurs during the update process.

    Returns:
        None
    """
    global IS_UPDATE_PRODUCT_DB_RUNNING
    try:
        if not IS_UPDATE_PRODUCT_DB_RUNNING:
            IS_UPDATE_PRODUCT_DB_RUNNING = 1
            all_current_products = get_all_products_from_sessions()
            # if the database for product is empty, we add the products to the database
            if collection_products.count_documents({}) == 0:
                for i, product in enumerate(all_current_products):
                    end_time_index = product.find(", end_time: ")
                    gelcoat_material_index = product.find(", gelcoat_material: ")
                    barrier_material_index = product.find(", barrier_material: ")
                    
                    start_time = product[len("start_time: "):end_time_index]
                    end_time = product[end_time_index + len(", end_time: "):gelcoat_material_index]
                    gelcoat_material = product[gelcoat_material_index + len(", gelcoat_material: "):barrier_material_index]
                    barrier_material = product[barrier_material_index + len(", barrier_material: "):]

                    document = {
                        "id": i+1,
                        "start_time": start_time,
                        "end_time": end_time,
                        "gelcoat_material": float(gelcoat_material),
                        "barrier_material": float(barrier_material),
                        "product_unique_identifier": product,
                        "comments": "",
                        "hide": 0
                    }
                    collection_products.insert_one(document)
            else:
                # get all old products from the database
                old_products = list(collection_products.find({}))
                old_products_unique_identifiers = {product["product_unique_identifier"] for product in old_products}

                # empty the database
                collection_products.delete_many({})

                # add all current products to the database, if they were in the old products, we keep their comments and hide status
                for i, product in enumerate(all_current_products):
                    end_time_index = product.find(", end_time: ")
                    gelcoat_material_index = product.find(", gelcoat_material: ")
                    barrier_material_index = product.find(", barrier_material: ")
                    
                    start_time = product[len("start_time: "):end_time_index]
                    end_time = product[end_time_index + len(", end_time: "):gelcoat_material_index]
                    gelcoat_material = product[gelcoat_material_index + len(", gelcoat_material: "):barrier_material_index]
                    barrier_material = product[barrier_material_index + len(", barrier_material: "):]
                    
                    document = {
                        "id": i+1,
                        "start_time": start_time,
                        "end_time": end_time,
                        "gelcoat_material": float(gelcoat_material),
                        "barrier_material": float(barrier_material),
                        "product_unique_identifier": product,
                        "comments": old_products[i]["comments"] if product in old_products_unique_identifiers else "",
                        "hide": old_products[i]["hide"] if product in old_products_unique_identifiers else 0
                    }
                    collection_products.insert_one(document)
            IS_UPDATE_PRODUCT_DB_RUNNING = 0
            logging.info("update_product_db < Done >")
        else:
            logging.info("update_product_db < The update product db is being calculated >")
    except Exception as e:
        IS_UPDATE_PRODUCT_DB_RUNNING = 0
        logging.error(f"update_product_db < Exception: {str(e)} >")


@app.route('/api/get_all_products_collection', methods=['GET'])
def get_all_products_collection():
    """
    Retrieves all products from the collection.

    Returns:
        A tuple containing the JSON response and the HTTP status code.
        
    Raises:
        Exception: If an error occurs during the retrieval process.
    """
    try:
        update_product_db()
        all_products = list(collection_products.find({
            "hide": 0
        }, {
            '_id': 0,
            "product_unique_identifier": 0,
        }).sort('id', -1))
        logging.info("get_all_products_collection < Done >")
        return jsonify(all_products), 200
    except Exception as e:
        logging.error(f"get_all_products_collection < Exception: {str(e)} >")
        return jsonify({"error get_all_products_collection": str(e)}), 500


@app.route('/api/set_hide_by_id_product', methods=['POST'])
def set_hide_by_id_product():
    """
    Sets the 'hide' attribute of a product in the collection_products database to 1.

    Returns:
        A JSON response indicating the status of the operation.
        
    Raises:
        Exception: If an error occurs during the update process
    """
    data = request.get_json()
    try:
        collection_products.update_one({"id": int(data['id'])}, {
            "$set": {"hide": 1}
        })
        logging.info(f"set_hide_by_id_product < id: {data['id']} >")
        return jsonify("Done"), 200
    except Exception as e:
        try:
            logging.error(f"set_hide_by_id_product < Exception: {str(e)} , id: {request.get_json()['id']} >")
        except Exception as e2:
            logging.error(f"set_hide_by_id_product < Exception 1: {str(e)}, Exception 2: {str(e2)} >")
        return jsonify({"error set_hide_by_id_product": str(e)}), 500


@app.route('/api/set_comments_by_id_product', methods=['POST'])
def set_comments_by_id_product():
    """
    Updates the comments of a product in the collection_products database based on the provided product ID.

    Returns:
        A JSON response indicating the status of the operation.
    """
    data = request.get_json()
    try:
        collection_products.update_one({"id": int(data['id'])}, {
            "$set": {"comments": data['comments']}
        })
        logging.info(f"set_comments_by_id_product < id: {data['id']} >")
        return jsonify("Done"), 200
    except Exception as e:
        try:
            logging.error(f"set_comments_by_id_product < Exception: {str(e)} , id: {request.get_json()['id']} >")
        except Exception as e2:
            logging.error(f"set_comments_by_id_product < Exception 1: {str(e)}, Exception 2: {str(e2)} >")
        return jsonify({"error set_comments_by_id_product": str(e)}), 500

@app.route('/api/get_all_deleted_products_collection', methods=['GET'])
def get_all_deleted_products_collection():
    """
    Retrieves all deleted products from the collection.

    Returns:
        A tuple containing the JSON response and the HTTP status code.
    """
    try:
        all_products = list(collection_products.find({
            "hide": 1
        }, {
            '_id': 0,
            "product_unique_identifier": 0,
        }).sort('id', -1))
        logging.info("get_all_deleted_products_collection < Done >")
        return jsonify(all_products), 200
    except Exception as e:
        logging.error(f"get_all_deleted_products_collection < Exception: {str(e)} >")
        return jsonify({"error get_all_deleted_products_collection": str(e)}), 500

@app.route('/api/restore_hide_by_id_product', methods=['POST'])
def restore_hide_by_id_product():
    """
    Restores the 'hide' attribute of a product by its ID.

    This function takes a JSON payload containing the ID of the product to be restored.
    It updates the 'hide' attribute of the product in the 'collection_products' collection to 0.
    If the update is successful, it logs the action and returns a JSON response with the message "Done" and status code 200.
    If an exception occurs during the update or logging process, it logs the exception and returns a JSON response with the error message and status code 500.

    Returns:
        A JSON response with the message "Done" and status code 200 if the update is successful.
        A JSON response with the error message and status code 500 if an exception occurs.
        
    Raises:
        Exception: If an error occurs during the update process.
    """
    data = request.get_json()
    try:
        collection_products.update_one({"id": int(data['id'])}, {
            "$set": {"hide": 0}
        })
        logging.info(f"restore_hide_by_id_product < id: {data['id']} >")
        return jsonify("Done"), 200
    except Exception as e:
        try:
            logging.error(f"restore_hide_by_id_product < Exception: {str(e)} , id: {request.get_json()['id']} >")
        except Exception as e2:
            logging.error(f"restore_hide_by_id_product < Exception 1: {str(e)}, Exception 2: {str(e2)} >")
        return jsonify({"error restore_hide_by_id_product": str(e)}), 500

##################################################################################### ?


@app.route('/api/get_nominal_sessions', methods=['POST'])
def get_nominal_sessions():
    """
    Retrieves the nominal sessions based on the pump type specified in the request data.

    Returns:
        A JSON response containing the list of nominal sessions and a status code.
        
    Raises:
        Exception: If an error occurs while retrieving the nominal sessions.
    """
    
    data = request.get_json()
    try:
        if data['pump_type'] == 'gelcoat':
            all_nominal_data = list(collection_nominal_gelcoat.find({}, {
                '_id': 0,
                'id': 1,
                'time_added': 1,
                'start_date': 1,
                'end_date': 1
            }))
        else:
            all_nominal_data = list(collection_nominal_barrier.find({}, {
                '_id': 0,
                'id': 1,
                'time_added': 1,
                'start_date': 1,
                'end_date': 1
            }))
        logging.info(f"get_nominal_sessions < pump_type: {data['pump_type']} >")
        return jsonify(all_nominal_data), 200
    except Exception as e:
        try:
            logging.error(f"get_nominal_sessions < Exception: {str(e)} , pump_type: {request.get_json()['pump_type']} >")
        except Exception as e2:
            logging.error(f"get_nominal_sessions < Exception 1: {str(e)}, Exception 2: {str(e2)} >")
        return jsonify({"error": str(e)}), 500



@app.route('/api/add_new_nominal_session', methods=['POST'])
def add_new_nominal_session():
    """
    Adds a new nominal session to the database based on the provided parameters.

    Returns:
        A JSON response containing the details of all the nominal sessions in the database.

    Raises:
        Exception: If an error occurs while adding the new nominal session.
    """
    global IS_ADD_NEW_NOMINAL_SESSION_RUNNING
    try:
        if not IS_ADD_NEW_NOMINAL_SESSION_RUNNING:
            IS_ADD_NEW_NOMINAL_SESSION_RUNNING = 1
            data = request.get_json()
            get_new_sessions()

            pump_type = data['pump_type']
            if pump_type == "gelcoat":
                collection_nominal_sessions = collection_nominal_gelcoat
                all_sessions = list(collection_sessions.find(
                    {"pump_type": "gelcoat", "is_trash": 0}))
            elif pump_type == "barrier":
                collection_nominal_sessions = collection_nominal_barrier
                all_sessions = list(collection_sessions.find(
                    {"pump_type": "barrier", "is_trash": 0}))
            else:
                IS_ADD_NEW_NOMINAL_SESSION_RUNNING = 0
                return jsonify({"error add_new_nominal_session_new": "Invalid pump type"}), 501

            size_collection_nominal_sessions = collection_nominal_sessions.count_documents({
            })
            start_date = data['startDate']
            end_date = data['endDate']

            # we find the session that are between the start_date and end_date

            id_offset = 1
            for session in all_sessions:
                if datetime.strptime(session['start_time'], '%Y-%m-%d %I:%M:%S %p') >= datetime.strptime(start_date, '%Y-%m-%d %I:%M:%S %p') and datetime.strptime(session['end_time'], '%Y-%m-%d %I:%M:%S %p') <= datetime.strptime(end_date, '%Y-%m-%d %I:%M:%S %p'):
                    # add the new nominal sessions to the database
                    document = {
                        "id": size_collection_nominal_sessions + id_offset,
                        "time_added": datetime.now().strftime('%Y-%m-%d %I:%M:%S %p'),
                        "start_date": session['start_time'],
                        "end_date": session['end_time'],
                        "total_sprayed_amount":session['total_sprayed_amount'],
                        "avg_speed":session['avg_speed'],
                        "avg_pressure":session['avg_pressure'],
                    }
                    collection_nominal_sessions.insert_one(document)
                    id_offset += 1
                # if the session is after the end_date, we break the loop
                if datetime.strptime(session['start_time'], '%Y-%m-%d %I:%M:%S %p') > datetime.strptime(end_date, '%Y-%m-%d %I:%M:%S %p'):
                    break

            all_nominal_data = list(collection_nominal_sessions.find({}, {
                '_id': 0,
                'id': 1,
                'time_added': 1,
                'start_date': 1,
                'end_date': 1
            }))
            IS_ADD_NEW_NOMINAL_SESSION_RUNNING = 0
            logging.info(f"add_new_nominal_session < pump_type: {data['pump_type']} >")
            return jsonify(all_nominal_data), 200
        else:
            logging.info("add_new_nominal_session < The add new nominal session is being calculated >")
            return jsonify("The add new nominal session is being calculated, please wait")
    except Exception as e:
        IS_ADD_NEW_NOMINAL_SESSION_RUNNING = 0
        try:
            data = request.get_json()
            logging.error(f"add_new_nominal_session < Exception: {str(e)}, pump_type: {data['pump_type']}, startDate: {data['startDate']}, endDate: {data['endDate']} >")
        except Exception as e2:
            logging.error(f"add_new_nominal_session < Exception 1: {str(e)}, Exception 2: {str(e2)} >")
        return jsonify({"error add_new_nominal_session_new": str(e)}), 500


def reset_id_nominal_sessions(collection):
    """
    Resets the ID of the nominal sessions in the specified collection.
    
    Args:
        collection (pymongo.collection.Collection): The collection containing the nominal sessions.
    
    Returns:
        None
    """
    all_data = list(collection.find({}, {
        '_id': 1,
        'id': 1
    }))
    for i in range(len(all_data)):
        collection.update_one({"_id": all_data[i]['_id']}, {
            "$set": {"id": i+1}
        })


@app.route('/api/remove_nominal_session_by_id', methods=['POST'])
def remove_nominal_session_by_id():
    """
    Removes a nominal session from the collection based on the provided ID.
    
    This function receives a JSON payload containing the pump type and the ID of the session to be removed.
    If the pump type is 'gelcoat', the session is removed from the 'collection_nominal_gelcoat' collection.
    If the pump type is not 'gelcoat', the session is removed from the 'collection_nominal_barrier' collection.
    
    Returns:
        A JSON response containing the details of all the nominal sessions in the database.
    
    Raises:
        Exception: If an error occurs while removing the session.
    """
    
    data = request.get_json()
    try:
        if data['pump_type'] == 'gelcoat':

            collection_nominal_gelcoat.delete_one({"id": int(data['id'])})

            reset_id_nominal_sessions(collection_nominal_gelcoat)
            all_nominal_data = list(collection_nominal_gelcoat.find({}, {
                '_id': 0,
                'id': 1,
                'time_added': 1,
                'start_date': 1,
                'end_date': 1
            }))
        else:
            collection_nominal_barrier.delete_one({"id": int(data['id'])})
            reset_id_nominal_sessions(collection_nominal_barrier)
            all_nominal_data = list(collection_nominal_barrier.find({}, {
                '_id': 0,
                'id': 1,
                'time_added': 1,
                'start_date': 1,
                'end_date': 1
            }))

        logging.info(f"remove_nominal_session_by_id < pump_type: {data['pump_type']}, id: {data['id']} >")
        return jsonify(all_nominal_data), 200
    except Exception as e:
        try:
            data = request.get_json()
            logging.error(f"remove_nominal_session_by_id < Exception: {str(e)}, pump_type: {data['pump_type']}, id: {data['id']} >")
        except Exception as e2:
            logging.error(f"remove_nominal_session_by_id < Exception 1: {str(e)}, Exception 2: {str(e2)} >")
        return jsonify({"error": str(e)}), 500

@app.route('/api/reset_maintenance_pump', methods=['GET'])
def reset_maintenance_pump():
    """
    Resets the maintenance pump records for gelcoat and barrier pumps.

    This function retrieves the maintenance pump records for gelcoat and barrier pumps from the database.
    If the records are not found, it adds new records with default values.
    It then updates the start time and end time of the existing records to the current time plus the default maintenance pump duration.
    Finally, it logs the completion of the reset operation and returns a JSON response indicating success.

    Returns:
        A JSON response indicating success and an HTTP status code of 200.

    Raises:
        Exception: If an error occurs during the reset operation, an exception is raised and a JSON response with the error message is returned.
    """
    
    try:
        maintenance_record_gelcoat = collection_maintenance_pump.find_one(
            {"pump_type": "gelcoat"})
        maintenance_record_barrier = collection_maintenance_pump.find_one(
            {"pump_type": "barrier"})
        # if didn't find, add the record with default value
        if maintenance_record_gelcoat is None or maintenance_record_barrier is None:
            document = {
                "pump_type": "gelcoat",
                "start_time": datetime.now(),
                "end_time": datetime.now() + timedelta(days=DEFAUL_MAINTEANCE_PUMP),
            }
            collection_maintenance_pump.delete_many({})
            collection_maintenance_pump.insert_one(document)
            document = {
                "pump_type": "barrier",
                "start_time": datetime.now(),
                "end_time": datetime.now() + timedelta(days=DEFAUL_MAINTEANCE_PUMP),
            }
            collection_maintenance_pump.insert_one(document)

            logging.info("reset_maintenance_pump < First Added >")
            return jsonify("Done"), 200

        # There is only a single record in the collection for each pump_type
        collection_maintenance_pump.update_one(
            {"_id": maintenance_record_gelcoat['_id']},
            {
                "$set": {
                    "start_time": datetime.now(),
                    "end_time": datetime.now() + timedelta(days=DEFAUL_MAINTEANCE_PUMP),
                }
            })
        collection_maintenance_pump.update_one(
            {"_id": maintenance_record_barrier['_id']},
            {
                "$set": {
                    "start_time": datetime.now(),
                    "end_time": datetime.now() + timedelta(days=DEFAUL_MAINTEANCE_PUMP),
                }
            })
        logging.info("reset_maintenance_pump < Done >")
        return jsonify("Done"), 200
    except Exception as e:
        logging.error(f"reset_maintenance_pump < Exception: {str(e)} >")
        return jsonify({"error": str(e)}), 501


@app.route('/api/reset_maintenance_filter', methods=['GET'])
def reset_maintenance_filter():
    """
    Resets the maintenance filter for the gelcoat and barrier pumps.

    This function retrieves the current maintenance filter records for the gelcoat and barrier pumps from the 
    'collection_maintenance_filter' collection. If the records do not exist, it adds them with default values.
    It then updates the start time and end time of the existing records to the current time plus the default 
    maintenance filter duration.

    Returns:
        A JSON response indicating the success of the operation.

    Raises:
        Exception: If an error occurs during the reset process.
    """
    
    try:
        maintenance_record_gelcoat = collection_maintenance_filter.find_one(
            {"pump_type": "gelcoat"})
        maintenance_record_barrier = collection_maintenance_filter.find_one(
            {"pump_type": "barrier"})
        
        # if didn't find, add the record with default value
        if maintenance_record_gelcoat is None or maintenance_record_barrier is None:
            document = {
                "pump_type": "gelcoat",
                "start_time": datetime.now(),
                "end_time": datetime.now() + timedelta(days=DEFAUL_MAINTEANCE_FILTER),
            }
            collection_maintenance_filter.delete_many({})
            collection_maintenance_filter.insert_one(document)
            document = {
                "pump_type": "barrier",
                "start_time": datetime.now(),
                "end_time": datetime.now() + timedelta(days=DEFAUL_MAINTEANCE_FILTER),
            }
            collection_maintenance_filter.insert_one(document)

            logging.info("reset_maintenance_filter < First Added >")
            return jsonify("Done"), 200

    # There is only a single record in the collection for each pump_type
        collection_maintenance_filter.update_one(
            {"_id": maintenance_record_gelcoat['_id']},
            {
                "$set": {
                    "start_time": datetime.now(),
                    "end_time": datetime.now() + timedelta(days=DEFAUL_MAINTEANCE_FILTER),
                }
            })
        collection_maintenance_filter.update_one(
            {"_id": maintenance_record_barrier['_id']},
            {
                "$set": {
                    "start_time": datetime.now(),
                    "end_time": datetime.now() + timedelta(days=DEFAUL_MAINTEANCE_FILTER),
                }
            })
        logging.info("reset_maintenance_filter < Done >")
        return jsonify("Done"), 200
    except Exception as e:
        logging.error(f"reset_maintenance_filter < Exception: {str(e)} >")
        return jsonify({"error": str(e)}), 501
    
@app.route('/api/get_maintenance', methods=['GET'])
def get_maintenance():
    """
    Retrieves the maintenance information for gelcoat and barrier pumps, as well as filter pumps.
    
    Returns:
        A JSON response containing the minimum number of days remaining for maintenance and filter changes.
        
    Raises:
        Exception: If an error occurs during the retrieval process, an error message is returned.
    """
    
    try:
        maintenance_record_gelcoat = collection_maintenance_pump.find_one(
            {"pump_type": "gelcoat"})
        maintenance_record_barrier = collection_maintenance_pump.find_one(
            {"pump_type": "barrier"})
        
        days_remaining_gelcoat = (maintenance_record_gelcoat['end_time'] - datetime.now()).days
        days_remaining_barrier = (maintenance_record_barrier['end_time'] - datetime.now()).days
        min_days_remaining_maintenance = str(min(days_remaining_gelcoat, days_remaining_barrier))
        
        filter_record_gelcoat = collection_maintenance_filter.find_one(
            {"pump_type": "gelcoat"})
        filter_record_barrier = collection_maintenance_filter.find_one(
            {"pump_type": "barrier"})
        days_remaining_gelcoat_filter = (filter_record_gelcoat['end_time'] - datetime.now()).days
        days_remaining_barrier_filter = (filter_record_barrier['end_time'] - datetime.now()).days
        min_days_remaining_filter = str(min(days_remaining_gelcoat_filter, days_remaining_barrier_filter))
        
        return jsonify({"maintenance": min_days_remaining_maintenance, "filter": min_days_remaining_filter}), 200
        
    except Exception as e:
        logging.error(f"get_maintenance < Exception: {str(e)} >")
        return jsonify({"error": str(e)}), 501

@app.route('/api/set_maintenance_manually', methods=['POST'])
def set_maintenance_manually():
    """
    Sets the maintenance manually based on the provided parameters.

    This function receives a JSON payload containing the pump type, field to change, and new value.
    It updates the maintenance records for the specified pump type and field with the new end time.
    The end time is calculated by adding the new value (in days) to the current date and time.

    Returns:
        - If the maintenance records are successfully updated, it returns a JSON response a status code of 200.

    Raises:
        Exception: If an error occurs during the process, an exception
    """
    
    try:
        data = request.get_json()
        pump_type = data['pump_type']
        field_to_change = data['field_to_change']
        new_value = int(data['new_value']) + 1  
        
        if pump_type == "gelcoat" and field_to_change == "filter":
            collection_maintenance_filter.update_one({"pump_type": "gelcoat"}, {
                "$set": {"end_time": datetime.now() + timedelta(days=int(new_value))}
            })
        elif pump_type == "gelcoat" and field_to_change == "pump":
            collection_maintenance_pump.update_one({"pump_type": "gelcoat"}, {
                "$set": {"end_time": datetime.now() + timedelta(days=int(new_value))}
            })
        elif pump_type == "barrier" and field_to_change == "filter":
            collection_maintenance_filter.update_one({"pump_type": "barrier"}, {
                "$set": {"end_time": datetime.now() + timedelta(days=int(new_value))}
            })
        elif pump_type == "barrier" and field_to_change == "pump":
            collection_maintenance_pump.update_one({"pump_type": "barrier"}, {
                "$set": {"end_time": datetime.now() + timedelta(days=int(new_value))}
            })
        else:
            pass
        logging.info(f"set_maintenance_manually < pump_type: {pump_type}, field_to_change: {field_to_change}, new_value: {new_value} >")
        return jsonify("Done Changinge Maintenance Record"), 200
    
    except Exception as e:
        try:
            data = request.get_json()
            logging.error(f"set_maintenance_manually < Exception: {str(e)}, pump_type: {data['pump_type']}, field_to_change: {data['field_to_change']}, new_value: {data['new_value']} >")
        except Exception as e2:
            logging.error(f"set_maintenance_manually < Exception 1: {str(e)}, Exception 2: {str(e2)} >")
        return jsonify({"error": str(e)}), 501
    

@app.route('/api/get_latest_alerts', methods=['GET'])
def get_latest_alerts():
    """
    Retrieves the latest alerts and nominal values from the database and sorts them by their times.
    
    Returns:
        A JSON response containing the sorted alerts and nominal values.
        
    Raises:
        Exception: If there is an error while retrieving the alerts from the database.
    """
    try:
        latest_alerts = list(collection_alerts.find({}, {}).sort('_id', -1).limit(10))
        latest_nominal = list(collection_alerts_nominal_values.find({}, {}).sort('_id', -1).limit(5))
        
        # sort alerts by their times
        all_alerts = []
        i = 0
        j = 0
        while i < len(latest_alerts) and j < len(latest_nominal):
            
            if datetime.strptime(latest_alerts[i]['time'], '%Y-%m-%d %I:%M:%S %p') > datetime.strptime(latest_nominal[j]['time'], '%Y-%m-%d %I:%M:%S %p'):
                all_alerts.append(latest_alerts[i])
                i += 1
            else:
                all_alerts.append(latest_nominal[j])
                j += 1
                
        while i < len(latest_alerts):
            all_alerts.append(latest_alerts[i])
            i += 1
            
        while j < len(latest_nominal):
            all_alerts.append(latest_nominal[j])
            j += 1
        
        # The _id is not serializable to JSON, so we remove it from the all_alerts
        for alert in all_alerts:
            alert["_id"] = 0
            
        logging.info("get_latest_alerts < Done >")
        return jsonify(all_alerts), 200
    except Exception as e:
        logging.error(f"get_latest_alerts < Exception: {str(e)} >")
        return jsonify({"error get_latest_alerts": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
