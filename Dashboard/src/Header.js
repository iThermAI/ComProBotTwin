// Header.js
import React from "react";
import "./Header.css";
import "./headers.css";

import "bootstrap/dist/css/bootstrap.min.css";

function Header() {
  return (
    <header className="p-3 mb-3 border-bottom " id="header-ch2t">
      <div className="container " id="container-ch2t">
        <div className="d-flex flex-wrap align-items-center justify-content-center justify-content-lg-start">
          <a
            href="/"
            className="d-flex align-items-center mb-2 mb-lg-0 link-body-emphasis text-decoration-none"
          >
            <svg
              className="bi me-2"
              width="40"
              height="32"
              role="img"
              aria-label="Bootstrap"
            >
              <use xlinkHref="#bootstrap" />
            </svg>
          </a>
          <a href="/Home" className="nav-link px-2 link-secondary">
            {" "}
            <img src="images/red_chart.PNG" />
          </a>

          <ul className="nav col-12 col-lg-auto me-lg-auto mb-2 justify-content-center mb-md-0">
            <li>
              <a href="/Dashboard" className="nav-link px-2 link-body-emphasis">
                {/* <img src="svg/speedometer2.svg" /> */}
                Dashboard
              </a>
            </li>
            <li>
              <a href="/Charts" className="nav-link px-2 link-body-emphasis">
                {/* <img src="svg/bar-chart-line.svg" /> */}
                Charts
              </a>
            </li>
            <li>
              <a href="/History" className="nav-link px-2 link-body-emphasis">
                {/* <img src="svg/speedometer2.svg" /> */}
                History
              </a>
            </li>
            <li>
              <a href="/Configurations" className="nav-link px-2 link-body-emphasis">
                {/* <img src="svg/speedometer2.svg" /> */}
                Configurations
              </a>
            </li>
            <li>
              <a
                href="/Maintenance"
                className="nav-link px-2 link-body-emphasis"
              >
                {" "}
                {/* <img src="svg/suitcase-lg.svg" /> */}
                Maintenance
              </a>
            </li>
            <li>
              <a href="/Sessions" className="nav-link px-2 link-body-emphasis">
                {/* <img src="svg/calendar2-date.svg" /> */}
                Sessions
              </a>
            </li>
            <li>
              <a href="/Products" className="nav-link px-2 link-body-emphasis">
                {/* <img src="svg/calendar2-date.svg" /> */}
                Products
              </a>
            </li>
          </ul>

          {/* <form
            className="col-12 col-lg-auto mb-3 mb-lg-0 me-lg-3"
            role="search"
          >
            <input
              type="search"
              className="form-control"
              placeholder="Search..."
              aria-label="Search"
            />
          </form> */}
          <ul className="nav col-12 col-lg-auto  mb-2 justify-content-center mb-md-0">
            <img src="images/logo.PNG" />
            <li>
              <a href="/Alerts" className="nav-link px-2 link-body-emphasis">
                <img src="svg/bell.svg" />
              </a>
            </li>{" "}
            <li>
              <a href="/Settings" className="nav-link px-2 link-body-emphasis">
                <img src="svg/gear.svg" />
              </a>
            </li>
          </ul>
          <div className="dropdown text-end">
            <a
              href="/"
              className="d-block link-body-emphasis text-decoration-none dropdown-toggle"
              data-bs-toggle="dropdown"
              aria-expanded="false"
            >
              <img src="svg/person-circle.svg" id="admin" />
            </a>

            {/* <ul className="dropdown-menu text-small">
              <li>
                <a className="dropdown-item" href="/">
                  New project...
                </a>
              </li>
              <li>
                <a className="dropdown-item" href="/">
                  Settings
                </a>
              </li>
              <li>
                <a className="dropdown-item" href="/">
                  Profile
                </a>
              </li>
              <li>
                <hr className="dropdown-divider" />
              </li>
              <li>
                <a className="dropdown-item" href="/">
                  Sign out
                </a>
              </li>
            </ul> */}
          </div>
        </div>
      </div>
    </header>
  );
}

export default Header;
