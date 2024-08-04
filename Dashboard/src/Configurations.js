import React, { useState } from 'react';
import { DateRangePicker } from 'rsuite';
import { FaCalendar } from 'react-icons/fa';
import axios from "axios";
import Dropdown_Config from './Dropdown_Config'; 
import './Configurations.css';
import moment from "moment";
import ipData from './ip_backend.json';

const Configurations = () => {
  const ip = ipData.ip;
  const [dateRange, setDateRange] = useState([]);
  const [selectedOption, setSelectedOption] = useState(null);
  const [data, setData] = useState([]);
  const [idToRemove, setIdToRemove] = useState('');
  const [showTable, setShowTable] = useState(true);

  const handleOptionChange = (selectedOption) => {
    setSelectedOption(selectedOption);
    
    if (selectedOption) {
      axios.post(`http://${ip}:5000/api/get_nominal_sessions`, {
      pump_type: selectedOption
    })
      .then(response => {
        console.log("response.data: ", response.data)
        setData(response.data);
        setShowTable(true);
      })
      .catch(error => {
        console.log("error: ", error)
      });
    }
  };

  const handleAddClick = () => {

    const startDateTemp = moment(dateRange[0]).format("YYYY-MM-DD hh:mm:ss A");
    const endDateTemp = moment(dateRange[1]).format("YYYY-MM-DD hh:mm:ss A");

    axios.post(`http://${ip}:5000/api/add_new_nominal_session`, {
      startDate: startDateTemp,
      endDate: endDateTemp,
      pump_type: selectedOption
    })
      .then(response => {
        setData(response.data);
        setShowTable(true);
      })
      .catch(error => {
        console.log("error: ", error)
      });
  };

  const handleRemoveClick = () => {
    axios.post(`http://${ip}:5000/api/remove_nominal_session_by_id`, {
      id: idToRemove, 
      pump_type: selectedOption
    })
      .then(response => {
        setData(response.data);
        setShowTable(true);
      })
      .catch(error => {
        console.log("error: ", error)
      });
  };

  const handleClearClick = () => {
    setData([]); 
  };

  return (
    <div className="row first-row history">
      <div className="section first-row-section">
        <button id="dashboard-button">Configs</button>
      </div>
      <div className="section first-row-section history">
        <div className="date-picker">
          <DateRangePicker
            format="yyyy/MMM/dd hh:mm:ss aa"
            size="lg"
            appearance="default"
            placeholder="Default"
            style={{ width: 450, marginTop: 8 }}
            value={dateRange}
            onChange={setDateRange}
            showMeridian
            caretAs={FaCalendar}
          />
        </div>
        <div className="section first-row-section history">
          <Dropdown_Config onOptionChange={handleOptionChange} />
        </div>
        <div className="section first-row-section history">
          <button id="apply-button" onClick={handleAddClick}>
            Add
          </button>

        </div>
        <div className="section first-row-section history">
          <input type="number" value={idToRemove} onChange={e => setIdToRemove(e.target.value)} />
          <button id="remove-button" onClick={handleRemoveClick}>
            Remove
          </button>
          {/* <button id="clear-button" onClick={handleClearClick}>
            Clear
          </button> */}
        </div>
      </div>
      <div className="table-container">
        {showTable && (
          <table className="styled-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Selected Date</th>
                <th>Time Added</th>
              </tr>
            </thead>
            <tbody>
              {data.map(item => (
                <tr key={item.id}>
                  <td>{item.id}</td>
                  <td>
                    {moment(item.start_date).format("YYYY-MM-DD")} <span style={{ color: "blue" }}>From</span> {moment(item.start_date).format("hh:mm:ss A")} <span style={{ color: "blue" }}>To</span> {moment(item.end_date).format("hh:mm:ss A")}
                  </td>

                  <td>{item.time_added}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default Configurations;