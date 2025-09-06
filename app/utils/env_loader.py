"""
Environment variable loader with validation and error handling.
"""

import os
import sys
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class EnvironmentLoader:
    """Environment variable loader with validation."""
    
    def __init__(self, env_file: str = ".env"):
        """
        Initialize environment loader.
        
        Args:
            env_file: Path to .env file
        """
        self.env_file = env_file
        self.loaded_vars = {}
        self.required_vars = [
            "FIREBASE_PROJECT_ID",
            "GOOGLE_CLOUD_PROJECT_ID", 
            "GOOGLE_CLOUD_STORAGE_BUCKET",
            "SECRET_KEY"
        ]
        self.optional_vars = [
            "FIREBASE_SERVICE_ACCOUNT_KEY_PATH",
            "FIREBASE_SERVICE_ACCOUNT_KEY_JSON",
            "ALLOWED_ORIGINS",
            "ENVIRONMENT",
            "DEBUG",
            "HOST",
            "PORT",
            "LOG_LEVEL"
        ]
    
    def load_environment(self) -> Dict[str, Any]:
        """
        Load environment variables from .env file and system environment.
        
        Returns:
            Dictionary of loaded environment variables
            
        Raises:
            SystemExit: If required variables are missing
        """
        try:
            # Load from .env file if it exists
            if Path(self.env_file).exists():
                self._load_from_file()
                logger.info(f"Loaded environment variables from {self.env_file}")
            else:
                logger.warning(f"Environment file {self.env_file} not found")
            
            # Override with system environment variables
            self._load_from_system()
            
            # Validate required variables
            self._validate_required_vars()
            
            # Set defaults for optional variables
            self._set_defaults()
            
            logger.info("Environment variables loaded successfully")
            return self.loaded_vars
            
        except Exception as e:
            logger.error(f"Failed to load environment variables: {e}")
            self._print_setup_instructions()
            sys.exit(1)
    
    def _load_from_file(self) -> None:
        """Load variables from .env file."""
        try:
            with open(self.env_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse key=value pairs
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        self.loaded_vars[key] = value
                    else:
                        logger.warning(f"Invalid line format in {self.env_file}:{line_num}: {line}")
                        
        except Exception as e:
            logger.error(f"Error reading {self.env_file}: {e}")
            raise
    
    def _load_from_system(self) -> None:
        """Load variables from system environment."""
        for var in self.required_vars + self.optional_vars:
            if var in os.environ:
                self.loaded_vars[var] = os.environ[var]
    
    def _validate_required_vars(self) -> None:
        """Validate that all required variables are present."""
        missing_vars = []
        
        for var in self.required_vars:
            if var not in self.loaded_vars or not self.loaded_vars[var]:
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    def _set_defaults(self) -> None:
        """Set default values for optional variables."""
        defaults = {
            "ALLOWED_ORIGINS": "http://localhost:3000,http://localhost:3001",
            "ENVIRONMENT": "development",
            "DEBUG": "true",
            "HOST": "0.0.0.0",
            "PORT": "8000",
            "LOG_LEVEL": "INFO"
        }
        
        for var, default_value in defaults.items():
            if var not in self.loaded_vars:
                self.loaded_vars[var] = default_value
    
    def _print_setup_instructions(self) -> None:
        """Print setup instructions for missing environment variables."""
        print("\n" + "="*60)
        print("🚨 ENVIRONMENT SETUP REQUIRED")
        print("="*60)
        print("\nTo run the VR 180 Video Processing Platform, you need to:")
        print("\n1. Create a .env file in the project root with the following variables:")
        print("\n   Required variables:")
        for var in self.required_vars:
            print(f"   - {var}=your_value_here")
        
        print("\n   Optional variables:")
        for var in self.optional_vars:
            print(f"   - {var}=your_value_here")
        
        print("\n2. Example .env file:")
        print("""
FIREBASE_PROJECT_ID=your-firebase-project-id
GOOGLE_CLOUD_PROJECT_ID=your-gcp-project-id
GOOGLE_CLOUD_STORAGE_BUCKET=your-gcs-bucket-name
SECRET_KEY=your-secret-key-here
FIREBASE_SERVICE_ACCOUNT_KEY_PATH=path/to/service-account-key.json
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
ENVIRONMENT=development
DEBUG=true
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
        """)
        
        print("\n3. Set up your Firebase and Google Cloud projects:")
        print("   - Create Firebase project and enable Authentication")
        print("   - Create Google Cloud project with Storage and Tasks APIs")
        print("   - Download Firebase service account key")
        print("   - Create GCS bucket for video storage")
        
        print("\n4. For testing without real credentials, you can use dummy values:")
        print("   - FIREBASE_PROJECT_ID=test-project")
        print("   - GOOGLE_CLOUD_PROJECT_ID=test-project")
        print("   - GOOGLE_CLOUD_STORAGE_BUCKET=test-bucket")
        print("   - SECRET_KEY=test-secret-key")
        
        print("\n" + "="*60)
    
    def get_var(self, key: str, default: Any = None) -> Any:
        """
        Get environment variable value.
        
        Args:
            key: Variable name
            default: Default value if not found
            
        Returns:
            Variable value or default
        """
        return self.loaded_vars.get(key, default)
    
    def set_var(self, key: str, value: Any) -> None:
        """
        Set environment variable value.
        
        Args:
            key: Variable name
            value: Variable value
        """
        self.loaded_vars[key] = value
        os.environ[key] = str(value)
    
    def list_vars(self) -> Dict[str, Any]:
        """
        List all loaded environment variables.
        
        Returns:
            Dictionary of all loaded variables
        """
        return self.loaded_vars.copy()
    
    def validate_firebase_setup(self) -> bool:
        """
        Validate Firebase setup.
        
        Returns:
            True if Firebase is properly configured
        """
        if not self.get_var("FIREBASE_PROJECT_ID"):
            return False
        
        # Check if service account key is available
        key_path = self.get_var("FIREBASE_SERVICE_ACCOUNT_KEY_PATH")
        key_json = self.get_var("FIREBASE_SERVICE_ACCOUNT_KEY_JSON")
        
        if key_path and Path(key_path).exists():
            return True
        elif key_json:
            return True
        
        return False
    
    def validate_gcp_setup(self) -> bool:
        """
        Validate Google Cloud Platform setup.
        
        Returns:
            True if GCP is properly configured
        """
        required = [
            "GOOGLE_CLOUD_PROJECT_ID",
            "GOOGLE_CLOUD_STORAGE_BUCKET"
        ]
        
        for var in required:
            if not self.get_var(var):
                return False
        
        return True


def load_environment(env_file: str = ".env") -> EnvironmentLoader:
    """
    Load environment variables with validation.
    
    Args:
        env_file: Path to .env file
        
    Returns:
        EnvironmentLoader instance with loaded variables
    """
    loader = EnvironmentLoader(env_file)
    loader.load_environment()
    return loader


def setup_environment_for_testing() -> EnvironmentLoader:
    """
    Set up environment variables for testing.
    
    Returns:
        EnvironmentLoader with test configuration
    """
    loader = EnvironmentLoader()
    
    # Set test values
    test_vars = {
        "FIREBASE_PROJECT_ID": "test-project",
        "GOOGLE_CLOUD_PROJECT_ID": "test-project",
        "GOOGLE_CLOUD_STORAGE_BUCKET": "test-bucket",
        "SECRET_KEY": "test-secret-key-for-development-only",
        "ENVIRONMENT": "testing",
        "DEBUG": "true",
        "HOST": "127.0.0.1",
        "PORT": "8000",
        "LOG_LEVEL": "DEBUG"
    }
    
    for key, value in test_vars.items():
        loader.set_var(key, value)
    
    logger.info("Environment set up for testing")
    return loader
