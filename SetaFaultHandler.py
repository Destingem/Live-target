import logging
import os
from datetime import datetime

class SetaFaultHandler:  # Renamed class
    def __init__(self, log_file="faults.log"):
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        log_path = os.path.join(log_dir, log_file)

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.ERROR)

        file_handler = logging.FileHandler(log_path)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)

    def log_fault(self, message):
        self.logger.error(message)

if __name__ == '__main__':
    # Example Usage
    fault_handler = SetaFaultHandler()
    fault_handler.log_fault("This is a test fault message.")
