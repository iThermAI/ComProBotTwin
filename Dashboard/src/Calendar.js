import React, { useState } from "react";
import Calendar from "react-calendar";
import "react-calendar/dist/Calendar.css"; 
import "./Calendar.css"; 
// Currently not functional, but the code is here for reference

const CalendarComponent = () => {
  const [date, setDate] = useState(new Date());
  const [reminders, setReminders] = useState([
    { date: "2024-03-26", reminder: "Project deadline" },
    { date: "2024-04-01", reminder: "Maintenance" },
  ]);

  const onChange = (newDate) => {
    setDate(newDate);
  };

  const formatDate = (date) => {
    return date.toISOString().split("T")[0];
  };

  const findRemindersForDay = (date) => {
    return reminders.filter((r) => r.date === formatDate(date));
  };

  return (
    <div className="dashboard">
      <div className="row">
        <div className="section first-row">
          <button id="dashboard-button">Calendar</button>
        </div>
      </div>
      <div className="row">
        <div className="section huge calendar">
          <Calendar
            className="cal"
            onChange={onChange}
            value={date}
            tileContent={({ date, view }) =>
              view === "month" &&
              findRemindersForDay(date).map((reminder, index) => (
                <p key={index} className="reminder">
                  {reminder.reminder}
                </p>
              ))
            }
          />
        </div>
      </div>
    </div>
  );
};

export default CalendarComponent;
