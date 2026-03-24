def encode_tlv(t: int, v: bytes) -> bytes:
    # Simple TLV: 1-byte type, 4-byte big-endian length, value
    length = len(v)
    return bytes([t]) + length.to_bytes(4, "big") + v


def create_tlv_for_image(image_bytes: bytes) -> bytes:
    # type 0x01: image payload
    return encode_tlv(0x01, image_bytes)
