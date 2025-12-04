
# background_service.py
import threading
import time
from enhanced_email_warmup import EnhancedEmailWarmupService
from database import DatabaseManager
from config import Config

class BackgroundWarmupService:
    def __init__(self):
        self.db_manager = DatabaseManager(Config.MONGO_URL, Config.DATABASE_NAME)
        self.warmup_service = EnhancedEmailWarmupService(self.db_manager)
        self.running = False
        self.thread = None
    
    def start(self):
        """Start the background warmup service"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_service, daemon=True)
            self.thread.start()
            print("🚀 Background warmup service started")
    
    def stop(self):
        """Stop the background warmup service"""
        self.running = False
        if self.thread:
            self.thread.join()
        print("⏹️  Background warmup service stopped")
    
    # def _run_service(self):
    #     """Main service loop"""
    #     while self.running:
    #         try:
    #             self.warmup_service.run_background_warmup_process()
    #         except Exception as e:
    #             print(f"❌ Background service error: {e}")
    #             time.sleep(300)  # Wait 5 minutes before retry