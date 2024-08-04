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
        className="dropdown-history"
        value={selectedOption}
        onChange={handleChange}
      >
        <option value="useful">Products</option>
        <option value="hidden">Hidden Products</option>
      </select>
    </div>
  );
};

export default DropdownSession;
