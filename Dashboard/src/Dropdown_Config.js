import React, { useState } from "react";

const Dropdown_Config = ({ onOptionChange }) => {
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
        <option value="barrier">Barrier</option>
        <option value="gelcoat">Gelcoat</option>
      </select>
    </div>
  );
};

export default Dropdown_Config;
