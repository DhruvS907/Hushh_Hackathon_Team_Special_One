// src/components/SlidebarMenu.jsx
import React from "react";
import { useNavigate } from "react-router-dom";
import { FiHome, FiMail, FiMessageSquare, FiClock, FiSettings, FiLogOut, FiBookOpen } from "react-icons/fi";
import "./SlidebarMenu.css";


function SidebarMenu({ isOpen, onClose }) {
  const navigate = useNavigate();

  const handleNavigation = (path) => {
    navigate(path);
    onClose();
  };

  const menuItems = [
    { icon: FiHome, label: "Home", path: "/home" },
    { icon: FiMail, label: "Email Summaries", path: "/Email_Summarizer" },
    { icon: FiMessageSquare, label: "Smart Replies", path: "/SmartReply" },
    { icon: FiClock, label: "Pending Responses", path: "/PendingResponses" },
    { icon: FiSettings, label: "Settings", path: "/settings" },
    { icon: FiBookOpen, label: "Manage Knowledge Base", path:"/knowledge-base"}
  ];

  if (!isOpen) return null;

  return (
    <div className="sidebar-overlay" onClick={onClose}>
      <div className="sidebar" onClick={(e) => e.stopPropagation()}>
        <h4>Menu</h4>
        <ul>
          {menuItems.map((item, index) => (
            <li key={index} onClick={() => handleNavigation(item.path)}>
              <item.icon className="menu-icon" />
              {item.label}
            </li>
          ))}
          <li onClick={() => handleNavigation("/")} className="logout-item">
            <FiLogOut className="menu-icon" />
            Logout
          </li>
        </ul>
      </div>
    </div>
  );
}

export default SidebarMenu;