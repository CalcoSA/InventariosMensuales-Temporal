from app.services.cache import ReadCache
from app.services.locking import SpreadsheetLocks
from app.services.retry import GoogleExecutor
from app.services.identity import IdentityService
from app.services.google_auth import GoogleAuthService
from app.services.google_drive import GoogleDriveService
from app.services.google_sheets import GoogleSheetsService
from app.repositories.monthly_bases import MonthlyBasesRepository
from app.repositories.monthly_inventory import MonthlyInventoryRepository
from app.repositories.monthly_generator import MonthlyGeneratorRepository
from app.services.monthly_inventory import MonthlyInventoryService
from app.services.monthly_admin import MonthlyAdminService
from app.services.monthly_cleanup import MonthlyCleanupService
from app.services.monthly_generator import MonthlyGeneratorService, MonthlyPreparationService


class Container:
    def __init__(self, config, *, drive=None, sheets=None, identity_provider=None):
        self.auth = GoogleAuthService(config["GOOGLE_CLIENT_FILE"], config["GOOGLE_TOKEN_FILE"])
        self.executor = GoogleExecutor()
        self.drive = drive or GoogleDriveService(self.auth, self.executor, config["GOOGLE_WRITES_ENABLED"])
        self.sheets = sheets or GoogleSheetsService(self.auth, self.executor, config["GOOGLE_WRITES_ENABLED"], config["TIMEZONE"])
        self.cache = ReadCache()
        self.locks = SpreadsheetLocks(config["RUNTIME_DIR"] / "locks")
        self.identity = IdentityService(identity_provider)
        self.bases = MonthlyBasesRepository(self.drive, self.sheets, self.cache, config["FORMATS_FOLDER_ID"])
        self.inventory_repository = MonthlyInventoryRepository(self.sheets, self.cache)
        self.inventory = MonthlyInventoryService(self.bases, self.inventory_repository, self.locks, config["TIMEZONE"])
        self.admin = MonthlyAdminService(self.bases, self.inventory_repository, self.identity)
        self.cleanup = MonthlyCleanupService(self.bases, self.inventory_repository, self.locks, config["TIMEZONE"])
        self.generator = MonthlyGeneratorService(MonthlyGeneratorRepository(self.drive, self.sheets), self.locks,
                        config["RUNTIME_DIR"] / "generator.json", config["MONTHLY_FOLDER_ID"], config["FORMATS_FOLDER_ID"], config["TIMEZONE"])
        self.preparation = MonthlyPreparationService(self.bases, self.locks)
