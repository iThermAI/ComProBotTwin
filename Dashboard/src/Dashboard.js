import React from "react";
import "./Dashboard.css";
import { useState } from "react";
import { useEffect } from "react";
import ReactECharts from "echarts-for-react";
import axios from "axios";
import ipData from './ip_backend.json';

const Dashboard = () => {
  const ip = ipData.ip;
  const [currentDate, setCurrentDate] = useState(new Date());
  useEffect(() => {
    const timer = setTimeout(() => {
      setCurrentDate(new Date());
    }, 24 * 60 * 60 * 1000 - (Date.now() % (24 * 60 * 60 * 1000)));

    return () => clearTimeout(timer);
  }, [currentDate]);

  const [chartDataBarrierSpeed, setChartDataBarrierSpeed] = useState(null);
  const [chartDataGelcoatSpeed, setChartDataGelcoatSpeed] = useState(null);
  const [gelcoatQuantity, setGelcoatQuantity] = useState(null);
  const [barrierQuantity, setBarrierQuantity] = useState(null);
  const [pressure, setPressure] = useState(null);
  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get(`http://${ip}:5000/api/get_20`);
        const data = response.data.data;
        setBarrierQuantity(response.data.total_weight_barr);
        setGelcoatQuantity(response.data.total_weight_gel);
        setPressure(response.data.pressure);

        setChartDataBarrierSpeed(formatChartDataBarrierSpeed(data));
        setChartDataGelcoatSpeed(formatChartDataGelcoatSpeed(data));
      } catch (error) {
        console.error("Error fetching data:", error);
      }
    };

    fetchData();

    const intervalId = setInterval(fetchData, 1500);
    return () => clearInterval(intervalId);
  }, []);

  const formatChartDataBarrierSpeed = (data) => {
    const formattedData = data.map((item) => ({
      datetime: item.time,
      speed: item.Barrier_speedRPM,
    }));

    formattedData.sort((a, b) => new Date(a.datetime) - new Date(b.datetime));

    const xAxisData = formattedData.map((item) => item.datetime);
    const seriesData = formattedData.map((item) => item.speed);

    return {
      dataZoom: [
        {
          type: "inside",
          filterMode: "none",
          xAxisIndex: 0,
          start: 60,
          end: 100,
        },
        {
          type: "inside",
          filterMode: "none",
          yAxisIndex: 0,
        },
      ],

      tooltip: {
        trigger: "axis",
      },
      xAxis: {
        name: "Time",
        type: "category",
        data: xAxisData,
        axisLabel: {
          formatter: function (value) {
            return value;
          },
        },
      },
      yAxis: {
        type: "value",
        name: "Speed",
        axisLabel: {
          formatter: "{value}",
        },
      },
      series: [
        {
          data: seriesData,
          type: "line",
          smooth: true,
        },
      ],
      title: {
        text: "Pump Speed (Barrier)",
        left: "center",
      },
    };
  };

  const formatChartDataGelcoatSpeed = (data) => {
    const formattedData = data.map((item) => ({
      datetime: item.time,
      speed: item.Gelcoat_speedRPM,
    }));

    formattedData.sort((a, b) => new Date(a.datetime) - new Date(b.datetime));

    const xAxisData = formattedData.map((item) => item.datetime);
    const seriesData = formattedData.map((item) => item.speed);

    return {
      dataZoom: [
        {
          type: "inside",
          filterMode: "none",
          xAxisIndex: 0,
          start: 60,
          end: 100,
        },
        {
          type: "inside",
          filterMode: "none",
          yAxisIndex: 0,
        },
      ],

      tooltip: {
        trigger: "axis",
      },
      xAxis: {
        name: "Time",
        type: "category",
        data: xAxisData,
        axisLabel: {
          formatter: function (value) {
            return value;
          },
        },
      },
      yAxis: {
        type: "value",
        name: "Speed",
        axisLabel: {
          formatter: "{value}",
        },
      },
      series: [
        {
          data: seriesData,
          type: "line",
          smooth: true,
        },
      ],
      title: {
        text: "Pump Speed (Gelcoat)",
        left: "center",
      },
    };
  };

  return (
    <div className="dashboard">
      <div className="row">
        <div className="section first-row">
          <button id="dashboard-button">Dashboard</button>
        </div>
      </div>
      <div className="row second-row">
        <div className="section large">
          <img
            src="images/pump1.PNG"
            alt="pump1"
            className="pump"
            id="pump-left"
          />
        </div>

        <div className="section x-large" id="chart-left">
          {chartDataBarrierSpeed && (
            <ReactECharts
              option={chartDataBarrierSpeed}
              style={{ height: "35vh", width: "35vw", minWidth: "450px" }}
            />
          )}
        </div>
        <div className="section x-large" id="chart-right">
          {chartDataGelcoatSpeed && (
            <ReactECharts
              option={chartDataGelcoatSpeed}
              style={{ height: "35vh", width: "35vw", minWidth: "450px" }}
            />
          )}
        </div>
        <div className="section large">
          {" "}
          <img
            src="images/pump2.PNG"
            alt="pump2"
            className="pump"
            id="pump-right"
          />
        </div>
      </div>
      <div className="row third-row">
        <div className="section small">
          <div className="section-box">
            <div className="content">
              <p className="pbox-dashboard">Barrier Quantity in the last 5 seconds</p>
              {barrierQuantity && <p id="material-weight"><strong>{barrierQuantity}</strong></p>}
            </div>
          </div>
        </div>
        
        <div className="section medium">
          {" "}
          <div className="section-box-temperature">
            <div className="content-temperature">
              <p>Pressure</p>
              <p>
              {pressure && <p >{pressure.toFixed(2)}</p>}
              </p>
            </div>
          </div>
        </div>
        <div className="section small">
          <div className="section-box">
            <div className="content">
              <p>Gelcoat Quantity in the last 5 seconds</p>
              
              {gelcoatQuantity && <p >{gelcoatQuantity.toFixed(2)}</p>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
