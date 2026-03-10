
import struct

# Constants
AMS2_PORT = 5606
PACKET_SIZE = 559

def parse_packet(data):
    if len(data) < 12:
        return None
    
    # 1. Header
    header = struct.unpack("<HHBBoBB", data[:12])
    # packet_number = header[0]
    # category_packet_number = header[1]
    # partial_packet_index = header[2]
    # partial_packet_number = header[3]
    packet_type = header[4]
    # packet_version = header[5]
    
    if packet_type != 0: # We only care about Telemetry (Type 0)
        return {'packet_type': packet_type}

    if len(data) < 559:
        return None
    
    payload = data[12:]
    
    # Using a format string for the first chunk of data
    # b (Game state)
    # b (Viewed)
    # B (Unfilt Throttle)
    # B (Unfilt Brake)
    # b (Unfilt Steer)
    # B (Unfilt Clutch)
    # B (Race State)
    # hHhHH (Temps/Pressures)
    # B (Fuel Cap)
    # B (Brake)
    # B (Throttle)
    # B (Clutch)
    # f (Fuel Level)
    # f (Speed)
    # H (RPM)
    # H (Max RPM)
    # b (Steering)
    # B (Gear)
    # B (Boost)
    # B (Crash)
    # f (Odometer)
    # fff (Orientation)
    # fff (Local Vel)
    # fff (World Vel)
    # fff (Angular Vel)
    # fff (Local Accel)
    # fff (World Accel)
    # fff (Extents)
    # BBBB (Tyre Flags)
    # BBBB (Terrain)
    # ffff (Tyre Y)
    # ffff (Tyre RPS)
    # BBBB (Tyre Temp - Wait, check size. usually u8)
    # ffff (Tyre Height)
    # BBBB (Tyre Wear)
    # BBBB (Brake Damage)
    # BBBB (Susp Damage)
    # hhhh (Brake TempCelsius)
    
    # Let's map critical metrics first to ensure we aren't misaligning by 1 byte
    # which ruins everything.
    
    # To start, we just extract by verified offsets if possible.
    # But since we built a hypothesis (Speed @ 29), let's try that.
    
    # Re-evaluating alignment:
    # 0-7: 7 bytes? No, bbBBbBB = 1+1+1+1+1+1+1 = 7.
    # 7-17: hHhHH = 2+2+2+2+2 = 10. (Total 17)
    # 17: B (FuelCap) -> 18.
    # 18: B (Brake) -> 19.
    # 19: B (Throt) -> 20.
    # 20: B (Clutch) -> 21.
    # 21: f (Fuel) -> 25.
    # 25: f (Speed) -> 29.
    
    try:
        # Use unpack_from for safety
        speed_ms = struct.unpack_from("<f", payload, 25)[0]
        full_throttle = struct.unpack_from("<B", payload, 19)[0] / 255.0
        brake = struct.unpack_from("<B", payload, 18)[0] / 255.0
        clutch = struct.unpack_from("<B", payload, 20)[0] / 255.0
        steering = struct.unpack_from("<b", payload, 33)[0] / 127.0 # offset 33? 29+2+2=33. Correct.
        rpm = struct.unpack_from("<H", payload, 29)[0]
        gear_raw = struct.unpack_from("<B", payload, 34)[0]
        odometer = struct.unpack_from("<f", payload, 37)[0]
        
        # G-Forces?
        # Local Acceleration is usually what we want for G-G.
        # Orientation (3f) -> 41+12 = 53
        # Local Vel (3f) -> 53+12 = 65
        # World Vel (3f) -> 65+12 = 77
        # Angular Vel (3f) -> 77+12 = 89
        # Local Accel (3f) -> 89. (X, Y, Z).
        
        accel_x = struct.unpack_from("<f", payload, 89)[0]
        accel_z = struct.unpack_from("<f", payload, 89 + 8)[0] # Z is usually Long? Or Y? Y is usually Up. X/Z are Lat/Lon?
        # In PCars2: X=Lat, Y=Vert, Z=Long.
        
        return {
            'packet_type': 0,
            'speed_kmh': speed_ms * 3.6,
            'rpm': rpm,
            'throttle': full_throttle,
            'brake': brake,
            'clutch': clutch,
            'steering': steering,
            'gear': gear_raw & 0x0F,
            'odometer_km': odometer, # Wait, usually raw value?
            'g_force_lat': accel_x / 9.81,
            'g_force_lon': accel_z / 9.81, 
        }
        
    except Exception as e:
        return None

