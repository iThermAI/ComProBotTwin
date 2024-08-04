import React from "react";
import "./Maintenance.css";
import { useState } from "react";
import { useEffect } from "react";
import Dropdown_Config from './Dropdown_Config'; 
import DropdownMaintenance from './DropdownMaintenance'; 
import axios from "axios";
import ipData from './ip_backend.json';

const Maintenance = () => {
  const ip = ipData.ip;
  console.log(ip);

  const [currentDate, setCurrentDate] = useState(new Date());
  const [maintenance, setMaintenance] = useState([]);
  const [filter, setFilter] = useState([]);
  const [selectedOption, setSelectedOption] = useState(null);
  const [selectedOptionMaterial, setSelectedOptionMaterial] = useState(null);
  const [numberOfDays, setnumberOfDays] = useState('0');
  useEffect(() => {
    const timer = setTimeout(() => {
      setCurrentDate(new Date());
    }, 24 * 60 * 60 * 1000 - (Date.now() % (24 * 60 * 60 * 1000)));

    return () => clearTimeout(timer);
  }, [currentDate]);

  useEffect(() => {
    axios
      .get(`http://${ip}:5000/api/get_maintenance`)
      .then((response) => {
        setMaintenance(response.data["maintenance"]);
        setFilter(response.data["filter"]);
      })
      .catch((error) => {
        setMaintenance([]);
        setFilter([]);
      });
  });
  
  const handleOptionChangeMaterial = (selectedOptionMaterial) => {
    setSelectedOptionMaterial(selectedOptionMaterial);
  }

  const handleOptionChange = (selectedOption) => {
    setSelectedOption(selectedOption);
  }

  const handleSetClick = () => {
    axios.post(`http://${ip}:5000/api/set_maintenance_manually`, {
      new_value: numberOfDays, 
      field_to_change: selectedOption,
      pump_type: selectedOptionMaterial
    })
    .then(response => {
      axios.get(`http://${ip}:5000/api/get_maintenance`)
        .then((response) => {
          setMaintenance(response.data["maintenance"]);
          setFilter(response.data["filter"]);
        })
        .catch((error) => {
          setMaintenance([]);
          setFilter([]);
        });
    })
    .catch(error => {
      console.log("error: ", error)
    });
  };

  const handleReset1 = async() => {
    try{
      const response = await axios.get(`http://${ip}:5000/api/reset_maintenance_pump`);
      axios.get(`http://${ip}:5000/api/get_maintenance`)
        .then((response) => {
          setMaintenance(response.data["maintenance"]);
          setFilter(response.data["filter"]);
        })
        .catch((error) => {
          setMaintenance([]);
          setFilter([]);
        });
    } catch (error) {
      console.log(error);
    }
  };

  const handleReset2 = async () => {
    try{
      const response = await axios.get(`http://${ip}:5000/api/reset_maintenance_filter`);
      axios.get(`http://${ip}:5000/api/get_maintenance`)
        .then((response) => {
          setMaintenance(response.data["maintenance"]);
          setFilter(response.data["filter"]);
        })
        .catch((error) => {
          setMaintenance([]);
          setFilter([]);
        });
    }  catch (error) {
      console.log(error);
    }

  };

  return (
    <div className="maintenance-container">
      <div className="row first-row-maintenace">
        <div className="section first-row-section-maintenace">
          <button id="dashboard-button">Maintenance</button>
        </div>
      </div>

      <div className="section first-row-section history">
        <div className="section first-row-section history">
          <Dropdown_Config onOptionChange={handleOptionChangeMaterial} />
        </div>
        <div className="section first-row-section history">
          <DropdownMaintenance onOptionChange={handleOptionChange} />
        </div>

        <div className="section first-row-section history">
          <input type="number" value={numberOfDays} onChange={e => setnumberOfDays(e.target.value)} />
          <button id="apply-button-session" onClick={handleSetClick}>
            Set Record
          </button>
        </div>
      </div>
      
      <div className="row second-row-maintenace">
        <div className="section second-row-section-maintenace">
          <div class="section-box-maintenance">
            <div class="content-maintenance">
              <p>Clean Spraygun</p>
              {maintenance && <p id="pump-filter-countdown">Days Left: {maintenance}</p>}
            </div>
          </div>
        </div>
      </div>
      <div className="row third-row-maintenace">
        <div className="section third-row-section-maintenace">
          <div class="section-box-maintenance">
            <div class="content-maintenance">
              <p>Change Pump Filters</p>
              
                {filter && <p id="pump-filter-countdown">Days Left: {filter} </p>}
              
            </div>
          </div>
        </div>
      </div>
      {/* Fourth Row */}
      {/* <div className="row fourth-row-maintenace">
        <div className="section third-row-section-maintenace">
          <div class="section-box-maintenance">
            <div class="content-maintenance">
              <p>Change Pump Lines</p>
              <p id="pump-filter-countdown">Days Left: 5</p>
            </div>
          </div>
        </div>
      </div> */}
      {/* Fifth Row */}
      <div className="row fifth-row-maintenace">
        <div className="section fifth-row-section-maintenace reset-buttons">
          <button onClick={handleReset1}>Spraygun Maintenance Reset</button>
          <button onClick={handleReset2}>Filter Maintenance Reset</button>
        </div>
      </div>
    </div>
  );
};

export default Maintenance;