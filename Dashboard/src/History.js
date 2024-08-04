import React from "react";
import "./History.css";
import { useState, useEffect } from "react";
import ReactECharts from "echarts-for-react";
import axios from "axios";
import DateRangePicker from "rsuite/DateRangePicker";
import "rsuite/DateRangePicker/styles/index.css";
import { FaCalendar } from "react-icons/fa";
import moment from "moment";
import Dropdown from "./Dropdown";
import ipData from './ip_backend.json';

const ChartsHistory = () => {
  const ip = ipData.ip;
  const queryParameters = new URLSearchParams(window.location.search)
  const pumpTypeParam = queryParameters.get("pumpType")
  const dataTypeCandidate = pumpTypeParam === "barrier" ? "Barrier_speedRPM" : "Gelcoat_speedRPM";
  const dataTypeNew = (pumpTypeParam === "barrier" || pumpTypeParam === "gelcoat") ? dataTypeCandidate : [];
  const [dataType, setDataType] = useState(dataTypeNew);
  const startDateParam = queryParameters.get("startDate")
  const endDateParam = queryParameters.get("endDate")
  
  const [currentDate, setCurrentDate] = useState(new Date());
  const [dateRange, setDateRange] = useState([]);
  const [dateRangeOut, setDateRangeOut] = useState([]);
  const [chartData, setChartData] = useState(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      setCurrentDate(new Date());
    }, 24 * 60 * 60 * 1000 - (Date.now() % (24 * 60 * 60 * 1000)));

    return () => clearTimeout(timer);
  }, [currentDate]);

  useEffect(() => {
    if (dateRange[0] && dateRange[1]) {
      const startDate = moment(dateRange[0]).format("YYYY-MM-DD hh:mm:ss A");
      const endDate = moment(dateRange[1]).format("YYYY-MM-DD hh:mm:ss A");
      setDateRangeOut([startDate, endDate]);
    }
  }, [dateRange]);

  useEffect(() => {
    if (startDateParam && endDateParam && dataType) {
      const fetchData = async () => {
        try {
          const response = await axios.post(
            `http://${ip}:5000/api/history`,
            {
              startDate: startDateParam,
              endDate: endDateParam,
            }
          );
          const data = response.data;
          setChartData(formatChartData(data));
        } catch (error) {
          console.error(error);
        }
      };
      fetchData();
    }
  }, [startDateParam, endDateParam, dataType]);

  const handleOptionChange = (option) => {
    setDataType(option);
  };

  const handleApplyClick = async () => {
    try {
      const response = await axios.post(
        `http://${ip}:5000/api/history`,
        {
          startDate: dateRangeOut[0],
          endDate: dateRangeOut[1],
        }
      );
      const data = response.data;
      setChartData(formatChartData(data));
    } catch (error) {
      console.error(error);
    }
  };

  const formatChartData = (data) => {
    const formattedData = data.map((item) => ({
      datetime: item.time,
      speed: item[dataType],
    }));
    
    formattedData.sort((a, b) => new Date(a.datetime) - new Date(b.datetime));

    const xAxisData = formattedData.map((item) => item.datetime);
    const seriesData = formattedData.map((item) => item.speed);

    return {
      dataZoom: [
        {
          type: "slider",
          filterMode: "none",
          xAxisIndex: 0,
          start: 60,
          end: 100,
        },
        {
          type: "slider",
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
            return value.split(" ")[1];
          },
        },
      },
      yAxis: {
        type: "value",
        name: "Value",
        scale: "true",
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
        text: dataType,
        left: "center",
      },
    };
  };

  return (
    <div className="charts-container">
      {/* First Row */}
      <div className="row first-row history">
        <div className="section first-row-section ">
          {" "}
          <button id="dashboard-button">History</button>
        </div>
        <div className="section first-row-section history">
          <div>
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
          </div>{" "}
          <div className="section first-row-section history">
            {" "}
            <Dropdown onOptionChange={handleOptionChange} />
          </div>
          <div className="section first-row-section history">
            {" "}
            <button id="apply-button" onClick={handleApplyClick}>
              Apply
            </button>
          </div>
        </div>

      </div>
      <div className="row" id="history-chart-row">
        <div className="section second-row-section" id="history-chart">
          {chartData && (
            <ReactECharts
              option={chartData}
              style={{
                height: "60vh",
                width: "90vw",
                minWidth: "420px",
              }}
            />
          )}
        </div>
        <div></div>
      </div>
    </div>
  );
};

export default ChartsHistory;
