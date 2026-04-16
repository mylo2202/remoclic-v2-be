class Settings:
    PROJECT_NAME: str = "REMOCLIC v2"
    # Central place to store configurations (this can be connected to pydantic BaseSettings later)
    FILE_PATH: str = "http://hpc.meteo.edu.vn/~tanpv/For_Me/562_VNU/PDF_Ope/202602/Dr_Prob.nc"

settings = Settings()
