import React, { useEffect, useState } from 'react';
import axios from "axios";
import DropdownSession from './DropdownProducts'; 
import './Products.css'; 
import moment from "moment";
import ipData from './ip_backend.json';
import { Link } from 'react-router-dom';


const Products = () => {
  const ip = ipData.ip;
  const [selectedOption, setSelectedOption] = useState(null);
  const [data, setData] = useState([]);
  const [idToRemove, setIdToRemove] = useState('0');
  const [showTable, setShowTable] = useState(true);
  const [hide, setHide] = useState(false);
  const [comment, setComment] = useState('');
  useEffect(() => {

    axios.get(`http://${ip}:5000/api/get_all_products_collection`)
      .then(response => {
        setData(response.data);
        setShowTable(true);
      })
      .catch(error => {
        console.log(error);
      });
  }, []);

  const handleOptionChange = (selectedOption) => {
    setSelectedOption(selectedOption);
    if (selectedOption === "useful") {
      setHide(false);
      axios.get(`http://${ip}:5000/api/get_all_products_collection`)
      .then(response => {
        setData(response.data);
        setShowTable(true);
      })
      .catch(error => {
        console.log(error);
      });
    }
    else {
      setHide(true);
      axios.get(`http://${ip}:5000/api/get_all_deleted_products_collection`).then(response => {
        setData(response.data);
        setShowTable(true);
      })
  };
}

  const handleSetCommentClick = () => {
    axios.post(`http://${ip}:5000/api/set_comments_by_id_product`, {
      id: idToRemove, 
      comments: comment
    })
      .then(response => {
        
        axios.get(`http://${ip}:5000/api/get_all_products_collection`).then(response => {
          setData(response.data);
          setShowTable(true);
        })
      })
      .catch(error => {
        console.log(error);  
      });

  };

  const handleRemoveClick = () => {
    axios.post(`http://${ip}:5000/api/set_hide_by_id_product`, {
      id: idToRemove, 
    })
      .then(response => {
        axios.get(`http://${ip}:5000/api/get_all_products_collection`).then(response => {
          setData(response.data);
          setShowTable(true);
        })
      })
      .catch(error => {
        console.log(error);
      });
  };

  const handleDeleteClick = (id) => {
    axios.post(`http://${ip}:5000/api/set_hide_by_id_product`, {
      id: id, 
    })
      .then(response => {
        axios.get(`http://${ip}:5000/api/get_all_products_collection`).then(response => {
          setData(response.data);
          setShowTable(true);
        })
      })
      .catch(error => {
        console.log(error);
      });
  };

  const handleRestoreClickWithId = () => {
    axios.post(`http://${ip}:5000/api/restore_hide_by_id_product`, {
      id: idToRemove, 
    })
      .then(response => {
        axios.get(`http://${ip}:5000/api/get_all_deleted_products_collection`).then(response => {
          setData(response.data);
          setShowTable(true);
        })
      })
      .catch(error => {
        console.log(error);
      });
  };

  const handleRestoreClick = (id) => {
    axios.post(`http://${ip}:5000/api/restore_hide_by_id_product`, {
      id: id, 
    })
      .then(response => {
        axios.get(`http://${ip}:5000/api/get_all_deleted_products_collection`).then(response => {
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
          
          {!hide && <button id="apply-button-session" onClick={handleSetCommentClick}>
            Set Comment
          </button>}
          
          {!hide && 
            <input type="text" id="comment-session" placeholder="Add Comment Here" value={comment} onChange={e => setComment(e.target.value)} />
          }
        </div>
        <div className="section first-row-section history">
          <input type="number" value={idToRemove} onChange={e => setIdToRemove(e.target.value)} />
          {!hide && 
          <button id="remove-button" onClick={handleRemoveClick}>
            Remove
          </button>}
          {hide &&
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
                <th>Gelcoat Sprayed</th>
                <th>Barrier Sprayed</th>
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
                  <td>{(item.gelcoat_material * 10).toFixed(2)} g</td>
                  <td>{(item.barrier_material * 10).toFixed(2)} g</td>

                  <td>
                    <Link to={`/History?startDate=${item.start_time}&endDate=${item.end_time}&pumpType=gelcoat`}>
                      Click to show
                    </Link>
                    <p>
                      {!hide && <a href="#" onClick={() => handleDeleteClick(item.id)}>Delete</a>}
                      {hide && <a href="#" onClick={() => handleRestoreClick(item.id)}>Restore</a>}
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

export default Products;