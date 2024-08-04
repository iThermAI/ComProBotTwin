import React, { useState } from "react";

const DropdownMaintenance = ({ onOptionChange }) => {
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
        className="dropdown-config"
        value={selectedOption}
        onChange={handleChange}
      >
        <option value="">Select...</option>
        <option value="filter">Filter</option>
        <option value="pump">Spraygun</option>
      </select>
    </div>
  );
};

export default DropdownMaintenance;
