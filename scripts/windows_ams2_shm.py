
import ctypes

# AMS2 / PCars2 Shared Memory Structure (Simplified)
# Name: "Local\$-cre-sm-p-cars-2-$-"

class SharedMemoryV2(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("mVersion", ctypes.c_uint),
        ("mBuildVersion", ctypes.c_uint),
        ("mGameState", ctypes.c_uint),
        ("mSessionState", ctypes.c_uint),
        ("mRaceState", ctypes.c_uint),
        
        # Participant Info
        ("mViewedParticipantIndex", ctypes.c_int),
        ("mNumParticipants", ctypes.c_int),
        ("mReserved", ctypes.c_byte * 256), # Simplified jump
        
        # Telemetry
        ("mUnfilteredThrottle", ctypes.c_ubyte),
        ("mUnfilteredBrake", ctypes.c_ubyte),
        ("mUnfilteredSteering", ctypes.c_byte),
        ("mUnfilteredClutch", ctypes.c_ubyte),
        
        ("mCarFlags", ctypes.c_ubyte),
        ("mOilTempCelsius", ctypes.c_short),
        ("mOilPressureKPa", ctypes.c_ushort),
        ("mWaterTempCelsius", ctypes.c_short),
        ("mWaterPressureKPa", ctypes.c_ushort),
        ("mFuelPressureKPa", ctypes.c_ushort),
        ("mFuelCapacity", ctypes.c_ubyte),
        ("mBrake", ctypes.c_ubyte),
        ("mThrottle", ctypes.c_ubyte),
        ("mClutch", ctypes.c_ubyte),
        ("mFuelLevel", ctypes.c_float),
        ("mSpeed", ctypes.c_float),
        ("mRpm", ctypes.c_float),
        ("mMaxRpm", ctypes.c_float),
        ("mSteering", ctypes.c_float),
        ("mGear", ctypes.c_int),
        ("mNumGears", ctypes.c_int),
        ("mBoostAmount", ctypes.c_float),
        ("mCrashState", ctypes.c_uint),
        ("mOdometerKM", ctypes.c_float),
        
        # Forces
        ("mOrientation", ctypes.c_float * 3),
        ("mLocalVelocity", ctypes.c_float * 3),
        ("mWorldVelocity", ctypes.c_float * 3),
        ("mAngularVelocity", ctypes.c_float * 3),
        ("mLocalAcceleration", ctypes.c_float * 3),
        ("mWorldAcceleration", ctypes.c_float * 3),
        ("mExtentsCentre", ctypes.c_float * 3),
        
        # Tyres
        ("mTyreFlags", ctypes.c_uint * 4),
        ("mTerrain", ctypes.c_uint * 4),
        ("mTyreY", ctypes.c_float * 4),
        ("mTyreRPS", ctypes.c_float * 4),
        ("mTyreSlipSpeed", ctypes.c_float * 4),
        ("mTyreTemp", ctypes.c_float * 4),
        ("mTyreGrip", ctypes.c_float * 4),
        ("mTyreHeightAboveGround", ctypes.c_float * 4),
        ("mTyreLateralStiffness", ctypes.c_float * 4),
        ("mTyreWear", ctypes.c_float * 4),
        ("mBrakeDamage", ctypes.c_float * 4),
        ("mSuspensionDamage", ctypes.c_float * 4),
        ("mBrakeTempCelsius", ctypes.c_float * 4),
        ("mTyreTreadTemp", ctypes.c_float * 4),
        ("mTyreLayerTemp", ctypes.c_float * 4),
        ("mTyreCarcassTemp", ctypes.c_float * 4),
        ("mTyreRimTemp", ctypes.c_float * 4),
        ("mTyreInternalAirTemp", ctypes.c_float * 4),
    ]

if __name__ == "__main__":
    print("--- AMS2 Struct Definitions ---")
    print("Este archivo solo contiene las estructuras de datos.")
    print("Para iniciar el forwarder, ejecuta:")
    print("python forward_ams2.py")
