import React, { useEffect, useState } from 'react';
import axios from "axios";
import DropdownSession from './DropdownSessions'; 
import './Sessions.css'; 
import moment from "moment";
import ipData from './ip_backend.json';
import { Link } from 'react-router-dom';

const Sessions = () => {
  
  const ip = ipData.ip;
  const [selectedOption, setSelectedOption] = useState(null);
  const [data, setData] = useState([]);
  const [idToRemove, setIdToRemove] = useState('0');
  const [showTable, setShowTable] = useState(true);
  const [trash, setTrash] = useState(false);
  const [comment, setComment] = useState('');

  useEffect(() => {
    axios.get(`http://${ip}:5000/api/get_all_sessions_from_collection`)
      .then(response => {
        setData(response.data);
        setShowTable(true);
      })
      .catch(error => {
        console.log(error);
      });
  }, [ip]);

  const handleOptionChange = (selectedOption) => {
    setSelectedOption(selectedOption);
    if (selectedOption === "useful") {
      setTrash(false);
      axios.get(`http://${ip}:5000/api/get_all_sessions_from_collection`)
      .then(response => {
        setData(response.data);
        setShowTable(true);
      })
      .catch(error => {
        console.log(error);
      });
    }
    else {
      setTrash(true);
      axios.get(`http://${ip}:5000/api/get_deleted_sessions_from_collection`).then(response => {
        setData(response.data);
        setShowTable(true);
      })
  };
}

  const handleSetCommentClick = () => {
    axios.post(`http://${ip}:5000/api/set_comments_by_id_session`, {
      id: idToRemove, 
      comments: comment
    })
      .then(response => {
        
        axios.get(`http://${ip}:5000/api/get_all_sessions_from_collection`).then(response => {
          setData(response.data);
          setShowTable(true);
        })
      })
      .catch(error => {
        console.log(error); 
      });

  };

  const handleRemoveClick = () => {
    axios.post(`http://${ip}:5000/api/set_trash_by_id`, {
      id: idToRemove, 
    })
      .then(response => {
        axios.get(`http://${ip}:5000/api/get_all_sessions_from_collection`).then(response => {
          setData(response.data);
          setShowTable(true);
        })
      })
      .catch(error => {
        console.log(error);
      });
  };

  const handleDeleteClick = (id) => {
    axios.post(`http://${ip}:5000/api/set_trash_by_id`, {
      id: id,
    })
      .then(response => {
        axios.get(`http://${ip}:5000/api/get_all_sessions_from_collection`).then(response => {
          setData(response.data);
          setShowTable(true);
        })
      })
      .catch(error => {
        console.log(error);
      });
  };

  const handleRestoreClick = (id) => {
    axios.post(`http://${ip}:5000/api/restore_trash_session_by_id`, {
      id: id,
    })
      .then(response => {
        axios.get(`http://${ip}:5000/api/get_deleted_sessions_from_collection`).then(response => {
          setData(response.data);
          setShowTable(true);
        })
      })
      .catch(error => {
        console.log(error);
      });
  };

  const handleRestoreClickWithId = () => {
    axios.post(`http://${ip}:5000/api/restore_trash_session_by_id`, {
      id: idToRemove, 
    })
      .then(response => {
        axios.get(`http://${ip}:5000/api/get_deleted_sessions_from_collection`).then(response => {
          setData(response.data);
          setShowTable(true);
        })
      })
      .catch(error => {
        console.log(error);
      });
  };


  return (
    <div className="row first-row history">
      <div className="section first-row-section">
        <button id="dashboard-button">Sessions</button>
      </div>
      <div className="section first-row-section history">

        <div className="section first-row-section history">
          <DropdownSession onOptionChange={handleOptionChange} />
        </div>
        <div className="section first-row-section history">
          {!trash && <button id="apply-button-session" onClick={handleSetCommentClick}>
            Set Comment
          </button>}
          
          {!trash && 
            <input type="text" id="comment-session" placeholder="Add Comment Here" value={comment} onChange={e => setComment(e.target.value)} />
          }


        </div>
        <div className="section first-row-section history">
          <input type="number" value={idToRemove} onChange={e => setIdToRemove(e.target.value)} />
          {!trash && 
          <button id="remove-button" onClick={handleRemoveClick}>
            Remove
          </button>}
          {trash &&
          <button id="restore-button" onClick={handleRestoreClickWithId}>
              Restore
          </button>}

        </div>
      </div>
      <div className="table-container">
        {showTable && (
          <table className="styled-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Date</th>
                <th>Pump Type</th>
                <th>Average Speed</th>
                <th>Sprayed Amount</th>
                <th>Actions</th>
                <th>Comment</th>
              </tr>
            </thead>
            <tbody>
              {data.map(item => (
                <tr key={item.id}>
                  <td>{item.id}</td>
                  <td>
                    {moment(item.start_time).format("YYYY-MM-DD")} <span style={{ color: "blue" }}>From</span> {moment(item.start_time).format("hh:mm:ss A")} <span style={{ color: "blue" }}>To</span> {moment(item.end_time).format("hh:mm:ss A")}
                  </td>
                  <td>{item.pump_type.charAt(0).toUpperCase() + item.pump_type.slice(1)}</td>
                  <td>{item.avg_speed.toFixed(2)}</td>
                  <td>{(item.total_sprayed_amount * 10).toFixed(2)} g</td>
                  <td>
                    <Link to={`/History?startDate=${item.start_time}&endDate=${item.end_time}&pumpType=${item.pump_type}`}>
                      Click to show
                    </Link>
                    <p>
                      
                      {!trash && <a href="#" onClick={() => handleDeleteClick(item.id)}>Delete</a>}
                      {trash && <a href="#" onClick={() => handleRestoreClick(item.id)}>Restore</a>}
                    </p>
                  </td>
                  <td>{item.comments}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};


export default Sessions;