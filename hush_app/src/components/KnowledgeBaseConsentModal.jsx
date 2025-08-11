import React from 'react';
import { Button, Modal, Row, Col } from 'react-bootstrap';
import { FiFileText, FiLock } from 'react-icons/fi';

const KnowledgeBaseConsentModal = ({ isOpen, onConsent, onDecline }) => {
  return (
    <Modal show={isOpen} onHide={onDecline} centered>
      <Modal.Header closeButton>
        <Modal.Title as="h5">
          <Row className="align-items-center">
            <Col xs="auto">
              <FiFileText size={28} className="text-primary" />
            </Col>
            <Col>
              Permission to Access Knowledge Base
            </Col>
          </Row>
        </Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <div className="d-flex align-items-center mt-3">
          <FiLock className="me-2" />
          <small>Your files will be processed and uploaded on our servers.</small>
        </div>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onDecline}>Decline</Button>
        <Button variant="primary" onClick={onConsent}>
          Allow Access
        </Button>
      </Modal.Footer>
    </Modal>
  );
};

export default KnowledgeBaseConsentModal;
