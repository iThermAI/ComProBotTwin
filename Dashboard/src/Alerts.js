import React from "react";
import "./Alerts.css";
import { useState } from "react";
import { useEffect } from "react";
import moment from "moment";
import axios from "axios";
import ipData from './ip_backend.json';

const Alerts = () => {
  const ip = ipData.ip;

  const [currentDate, setCurrentDate] = useState(new Date());
  const [alerts, setAlerts] = useState([]);
  useEffect(() => {
    const timer = setTimeout(() => {
      setCurrentDate(new Date());
    }, 24 * 60 * 60 * 1000 - (Date.now() % (24 * 60 * 60 * 1000)));

    return () => clearTimeout(timer);
  }, [currentDate]);

  useEffect(() => {
    axios
      .get(`http://${ip}:5000/api/get_latest_alerts`)
      .then((response) => {
        setAlerts(response.data);
      })
      .catch((error) => {
        setAlerts([]);
      });
    
  }, []);


  return (
    <div className="charts-container">
      <div className="row first-row">
        <div className="section first-row-section">
          {" "}
          <button id="dashboard-button">Alerts</button>
        </div>
        <div className="section first-row-section"> </div>
      </div>
      {
            alerts && alerts.map((alert, index) => {
              return (

                <div className="row">
                  <div className="section huge alert">
                  <div className="text-side" key={index}>
                      <p id="pump-alert">
                        <strong>{alert.message}</strong>
                      </p>
                      <p id="block-notification">
                        {alert.more_info}
                      </p>
                      <p id="time-alert"> {moment(alert.time).format("MMMM Do YYYY, h:mm:ss a")}</p>
                  </div>
                </div>
                </div>
              );
            })
          }
      <div>
        {" "}
        <div id="temporary" className="section huge alert "></div>
      </div>
    </div>
  );
};

export default Alerts;
