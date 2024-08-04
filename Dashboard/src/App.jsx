import React, { useEffect } from "react";
import Header from "./Header";
import "./App.css";
import HomePage from "./HomePage"; 
import Dashboard from "./Dashboard";
import Charts from "./Charts";
import Maintenance from "./Maintenance";
import Alerts from "./Alerts";
import Settings from "./Settings";
import MyLiveChartComponent from "./Calendar";
import RedirectToHome from "./Redirect";
import ChartsHistory from "./History";
import Configurations from "./Configurations";
import Sessions from "./Sessions";
import Products from "./Products";

import { BrowserRouter as Router, Routes, Route } from "react-router-dom";

const App = () => {
  return (
    <Router>
      <div className="app">
        <Header />
        <div className="app-body">
          <div className="main-content">
            <Routes>
              <Route exact path="/" element={<RedirectToHome />} />
              <Route exact path="/Home" element={<HomePage />} />
              <Route path="/Dashboard" element={<Dashboard />} />
              <Route path="/Charts" element={<Charts />} />
              <Route path="/History" element={<ChartsHistory />} />
              <Route path="/Maintenance" element={<Maintenance />} />
              <Route path="/Alerts" element={<Alerts />} />
              <Route path="/Settings" element={<Settings />} />
              <Route path="/Configurations" element={<Configurations />} />
              <Route path="/Calendar" element={<MyLiveChartComponent />} />
              <Route path="/Sessions" element={<Sessions />} />
              <Route path="/Products" element={<Products />} />
            </Routes>
          </div>
        </div>
      </div>
    </Router>
  );
};

export default App;
