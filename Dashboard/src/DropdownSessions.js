import React, { useState } from "react";

const DropdownSession = ({ onOptionChange }) => {
  const [selectedOption, setSelectedOption] = useState("useful");

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
        <option value="useful">Sessions</option>
        <option value="trash">Deleted Sessions</option>
      </select>
    </div>
  );
};

export default DropdownSession;
