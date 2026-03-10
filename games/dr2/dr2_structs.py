"""
Dirt Rally 2.0 - UDP Telemetry Packet Parser
Format: 66 little-endian floats (264 bytes) with extradata=3

Game config path (Windows):
  C:/Users/diean/OneDrive/Documentos/My Games/DiRT Rally 2.0/hardwaresettings/hardware_settings_config.xml

Enable UDP:
  <udp enabled="true" extradata="3" ip="WSL_IP" port="20777" delay="1" />
"""

import struct

# Packet format: 66 little-endian floats
DR2_PACKET_FORMAT = '<66f'
DR2_PACKET_SIZE = struct.calcsize(DR2_PACKET_FORMAT)  # 264 bytes

# Field names mapped to their index in the float array
DR2_FIELDS = {
    'total_time':       0,   # Total run time (seconds)
    'lap_time':         1,   # Current stage time (seconds)
    'lap_distance':     2,   # Distance in current lap/stage (meters)
    'total_distance':   3,   # Total distance (meters)
    'pos_x':            4,   # World position X
    'pos_y':            5,   # World position Y
    'pos_z':            6,   # World position Z
    'speed':            7,   # Speed (m/s)
    'vel_x':            8,   # Velocity X
    'vel_y':            9,   # Velocity Y
    'vel_z':            10,  # Velocity Z
    'roll_x':           11,  # Forward direction X (roll vector)
    'roll_y':           12,  # Forward direction Y
    'roll_z':           13,  # Forward direction Z
    'pitch_x':          14,  # Right direction X (pitch vector)
    'pitch_y':          15,  # Right direction Y
    'pitch_z':          16,  # Right direction Z
    'susp_pos_rl':      17,  # Suspension position Rear Left
    'susp_pos_rr':      18,  # Suspension position Rear Right
    'susp_pos_fl':      19,  # Suspension position Front Left
    'susp_pos_fr':      20,  # Suspension position Front Right
    'susp_vel_rl':      21,  # Suspension velocity Rear Left
    'susp_vel_rr':      22,  # Suspension velocity Rear Right
    'susp_vel_fl':      23,  # Suspension velocity Front Left
    'susp_vel_fr':      24,  # Suspension velocity Front Right
    'wheel_speed_rl':   25,  # Wheel speed Rear Left
    'wheel_speed_rr':   26,  # Wheel speed Rear Right
    'wheel_speed_fl':   27,  # Wheel speed Front Left
    'wheel_speed_fr':   28,  # Wheel speed Front Right
    'throttle':         29,  # Throttle input 0.0-1.0
    'steer':            30,  # Steering input -1.0 to 1.0
    'brake':            31,  # Brake input 0.0-1.0
    'clutch':           32,  # Clutch input 0.0-1.0
    'gear':             33,  # Current gear (0=N, 10=R, 1-7=forward)
    'g_force_lat':      34,  # Lateral G-force
    'g_force_lon':      35,  # Longitudinal G-force
    'current_lap':      36,  # Current lap number
    'rpm':              37,  # Engine RPM (raw: rpm/10)
    # Indices 38-58: brake temps, wheel positions, etc (extradata=3)
    'sector1_time':     38,  # Sector 1 time (not always populated)
    'sector2_time':     39,  # Sector 2 time
    'brake_temp_rl':    40,  # Brake temperature Rear Left
    'brake_temp_rr':    41,  # Brake temperature Rear Right
    'brake_temp_fl':    42,  # Brake temperature Front Left
    'brake_temp_fr':    43,  # Brake temperature Front Right
    # Tyre/surface data
    'laps_complete':    44,  # Laps/stages completed
    'total_laps':       45,  # Total laps (0 in rally)
    'track_length':     46,  # Track/stage length (meters)
    'last_lap_time':    47,  # Last lap/stage time
    # More extended data
    'max_rpm':          48,  # Max RPM (raw: rpm/10)
    'idle_rpm':         49,  # Idle RPM (raw: rpm/10)
    'max_gears':        50,  # Number of gears
    # Positions 51-65: additional motion/physics data
    'car_pos_x':        51,  # Car position (duplicate or refined)
    'car_pos_y':        52,
    'car_pos_z':        53,
    'speed_mph':        54,  # Speed in mph (might be 0)
    'turbo_pressure':   55,
    'air_temp':         56,  # Air temperature
    'oil_temp_unused':  57,  # Oil temperature (may be 0)
    'oil_pressure':     58,  # Oil pressure (may be 0)
    'handbrake':        59,  # Handbrake input 0.0-1.0
    # Padding / game specific
    'yaw_rate':         60,
    'pitch_rate':       61,
    'roll_rate':        62,
    'front_downforce':  63,  # May not be populated
    'rear_downforce':   64,  # May not be populated
    'water_temp':       65,  # Water/coolant temp
}


def parse_packet(data):
    """Parse a 264-byte DR2 UDP packet into a named dict"""
    if len(data) < DR2_PACKET_SIZE:
        return None

    values = struct.unpack(DR2_PACKET_FORMAT, data[:DR2_PACKET_SIZE])
    
    packet = {}
    for name, idx in DR2_FIELDS.items():
        packet[name] = values[idx]
    
    # Post-processing
    packet['speed_kmh'] = packet['speed'] * 3.6  # m/s → km/h
    packet['rpm'] = packet['rpm'] * 10            # Raw is rpm/10
    packet['max_rpm'] = packet['max_rpm'] * 10
    packet['idle_rpm'] = packet['idle_rpm'] * 10
    packet['gear_display'] = int(packet['gear'])   # 0=N, 10=R, 1-7=fwd
    
    # Wheel slip (ratio of wheel speed to car speed)
    if packet['speed'] > 1.0:
        for wheel in ['rl', 'rr', 'fl', 'fr']:
            ws = abs(packet[f'wheel_speed_{wheel}'])
            packet[f'slip_{wheel}'] = abs(ws - packet['speed']) / packet['speed']
    else:
        for wheel in ['rl', 'rr', 'fl', 'fr']:
            packet[f'slip_{wheel}'] = 0.0
    
    return packet


def get_raw_values(data):
    """Parse raw float array (for debugging)"""
    if len(data) < DR2_PACKET_SIZE:
        return None
    return struct.unpack(DR2_PACKET_FORMAT, data[:DR2_PACKET_SIZE])
