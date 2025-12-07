"""
Configuration management module
Responsible for loading and managing application configuration
"""
import os

class Config:
    """Configuration management class"""
    
    def __init__(self):
        # External notification config
        self.bot_token = None
        self.chat_id = None
        self.webhook_key = None
        self.default_ext_notify = None
        self.telegram_loaded = False
        self.wechat_loaded = False
    
    def load_config(self, config_path=None):
        """
        Load configuration file
        """
        if config_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            config_path = os.path.join(parent_dir, "agent.conf")
        
        print(f"Attempting to load configuration file: {config_path}")
        
        if not os.path.exists(config_path):
            print(f"Configuration file does not exist: {config_path}")
            print("Using default configuration values")
            return False
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # External notification config
                        if key == 'Bot_Token':
                            self.bot_token = value
                            print(f"Loaded Bot_Token: {self.bot_token[:10] if self.bot_token else 'None'}...")
                        elif key == 'Chat_ID':
                            self.chat_id = value
                            print(f"Loaded Chat_ID: {self.chat_id}")
                        elif key == 'Webhook_Key':
                            self.webhook_key = value
                            print(f"Loaded Webhook_Key: {self.webhook_key[:10] if self.webhook_key else 'None'}...")
                        elif key == 'Default_ExtNotify':
                            self.default_ext_notify = value.lower()
                            print(f"Loaded Default_ExtNotify: {self.default_ext_notify}")
            
            # Check Telegram configuration
            if self.bot_token and self.chat_id:
                print("Telegram configuration loaded successfully")
                self.telegram_loaded = True
            else:
                print("Telegram configuration incomplete")
                self.telegram_loaded = False
            
            # Check WeChat Work configuration
            if self.webhook_key:
                print("WeChat Work configuration loaded successfully")
                self.wechat_loaded = True
            else:
                print("WeChat Work configuration incomplete")
                self.wechat_loaded = False
            
            # Validate default notification configuration
            if self.default_ext_notify:
                if self.default_ext_notify not in ['wechat', 'telegram']:
                    print(f"Warning: Invalid Default_ExtNotify configuration: {self.default_ext_notify}, should be 'Wechat' or 'Telegram'")
                    self.default_ext_notify = None
                else:
                    print(f"Default external notification platform: {self.default_ext_notify}")
            
            # If no default platform is set, automatically select an available one
            if not self.default_ext_notify:
                if self.wechat_loaded:
                    self.default_ext_notify = 'wechat'
                    print("Automatically selected WeChat Work as default notification platform")
                elif self.telegram_loaded:
                    self.default_ext_notify = 'telegram'
                    print("Automatically selected Telegram as default notification platform")
                else:
                    print("Warning: No available external notification platform")
            
            return self.telegram_loaded or self.wechat_loaded
                
        except Exception as e:
            print(f"Failed to load configuration file: {e}")
            print("Using default configuration values")
            return False
    
    def get_telegram_config(self):
        """Get Telegram configuration"""
        return self.bot_token, self.chat_id
    
    def get_wechat_config(self):
        """Get WeChat Work configuration"""
        return self.webhook_key
    
    def get_default_ext_notify(self):
        """Get default external notification platform"""
        return self.default_ext_notify
    
    def get_available_notifiers(self):
        """Get all available notification platforms"""
        available = []
        if self.is_telegram_configured():
            available.append('telegram')
        if self.is_wechat_configured():
            available.append('wechat')
        return available
    
    def set_telegram_config(self, bot_token, chat_id):
        """Manually set Telegram configuration"""
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.telegram_loaded = True
        print(f"Manually set Telegram configuration")
    
    def set_wechat_config(self, webhook_key):
        """Manually set WeChat Work configuration"""
        self.webhook_key = webhook_key
        self.wechat_loaded = True
        print(f"Manually set WeChat Work configuration")
    
    def set_default_ext_notify(self, platform):
        """Manually set default notification platform"""
        platform = platform.lower()
        if platform in ['wechat', 'telegram']:
            self.default_ext_notify = platform
            print(f"Set default notification platform: {platform}")
        else:
            print(f"Invalid notification platform: {platform}")
    
    def is_telegram_configured(self):
        """Check if Telegram is configured"""
        return self.telegram_loaded and self.bot_token and self.chat_id
    
    def is_wechat_configured(self):
        """Check if WeChat Work is configured"""
        return self.wechat_loaded and self.webhook_key

# Global configuration instance
app_config = Config()

def load_config(config_path=None):
    """Load configuration file"""
    return app_config.load_config(config_path)

def get_telegram_config():
    """Get Telegram configuration"""
    return app_config.get_telegram_config()

def get_wechat_config():
    """Get WeChat Work configuration"""
    return app_config.get_wechat_config()

def get_default_ext_notify():
    """Get default external notification platform"""
    return app_config.get_default_ext_notify()

def get_available_notifiers():
    """Get all available notification platforms"""
    return app_config.get_available_notifiers()

def set_telegram_config(bot_token, chat_id):
    """Manually set Telegram configuration"""
    return app_config.set_telegram_config(bot_token, chat_id)

def set_wechat_config(webhook_key):
    """Manually set WeChat Work configuration"""
    return app_config.set_wechat_config(webhook_key)

def set_default_ext_notify(platform):
    """Manually set default notification platform"""
    return app_config.set_default_ext_notify(platform)

def is_telegram_configured():
    """Check if Telegram is configured"""
    return app_config.is_telegram_configured()

def is_wechat_configured():
    """Check if WeChat Work is configured"""
    return app_config.is_wechat_configured()