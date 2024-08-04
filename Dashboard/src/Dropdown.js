import React, { useState } from "react";

const Dropdown = ({ onOptionChange }) => {
  const [selectedOption, setSelectedOption] = useState("");

  const handleChange = (event) => {
    setSelectedOption(event.target.value);
    if (onOptionChange) {
      onOptionChange(event.target.value);
    }
  };

  return (
    <div>
      <select
        className="dropdown-history"
        value={selectedOption}
        onChange={handleChange}
      >
        <option value="">Select...</option>
        <option value="Barrier_speedRPM">Pump Speed (Barrier)</option>
        <option value="Gelcoat_speedRPM">Pump Speed (Gelcoat)</option>
        <option value="Gelcoat_pulses">Pulses (Gelcoat)</option>
        <option value="Barr_pulses">Pulses (Barrier)</option>
        <option value="Pressure">Pressure</option>
        <option value="WaterLevel_2">Water Level</option>
      </select>
    </div>
  );
};

export default Dropdown;
