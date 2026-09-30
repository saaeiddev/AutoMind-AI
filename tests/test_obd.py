from obd.protocol import decode_pid, decode_vin, parse_dtc_response, parse_supported_pids


def test_parse_stored_dtcs():
    # 01 71 -> P0171, 03 02 -> P0302
    assert parse_dtc_response("43 01 71 03 02 00 00\r>") == ["P0171", "P0302"]


def test_parse_pending_dtc():
    assert parse_dtc_response("47 03 00\r>", 0x47) == ["P0300"]


def test_decode_rpm():
    assert decode_pid("0C", "41 0C 1A F8\r>") == 1726.0


def test_decode_coolant():
    assert decode_pid("05", "41 05 7B\r>") == 83


def test_decode_voltage():
    assert decode_pid("42", "41 42 36 B0\r>") == 14.0


def test_supported_pids():
    pids = parse_supported_pids("41 00 BE 1F A8 13\r>", 0x00)
    assert "01" in pids
    assert "20" in pids


def test_decode_vin_multiline():
    raw = "49 02 01 57 50 30 5A 5A 5A\r49 02 02 39 39 5A 54 53 33 39\r49 02 03 32 31 32 34 31\r>"
    vin = decode_vin(raw)
    assert vin == "WP0ZZZ99ZTS392124"


def test_decode_compact_elm_response_with_spaces_off():
    assert decode_pid("0C", "410C1AF8\r>") == 1726.0
    assert parse_dtc_response("43017103020000\r>") == ["P0171", "P0302"]


def test_elm327_client_with_simulated_transport():
    from obd.elm327 import ELM327Client
    from obd.transport import OBDTransport

    class FakeTransport(OBDTransport):
        def __init__(self):
            self.opened = False
            self.commands = []

        def open(self):
            self.opened = True

        def close(self):
            self.opened = False

        @property
        def is_open(self):
            return self.opened

        def transact(self, command: str) -> str:
            self.commands.append(command)
            replies = {
                "ATI": "ELM327 v1.5\r>",
                "ATDP": "AUTO, ISO 15765-4 (CAN 11/500)\r>",
                "ATRV": "14.1V\r>",
                "0100": "41 00 FF FF FF FF\r>",
                "0120": "41 20 FF FF FF FF\r>",
                "0140": "41 40 FF FF FF FF\r>",
                "0160": "41 60 00 00 00 00\r>",
                "010C": "41 0C 1A F8\r>",
                "03": "43 01 71 00 00\r>",
                "07": "47 00 00\r>",
                "0A": "4A 00 00\r>",
                "0902": "49 02 01 57 50 30 5A 5A 5A\r49 02 02 39 39 5A 54 53 33 39\r49 02 03 32 31 32 34 31\r>",
            }
            return replies.get(command, "OK\r>")

    transport = FakeTransport()
    client = ELM327Client(transport)
    info = client.connect()
    assert client.connected
    assert "ELM327" in info.identity
    assert client.read_pid("0C").value == 1726.0
    assert client.read_stored_dtcs() == ["P0171"]
    assert client.read_vin() == "WP0ZZZ99ZTS392124"
    client.disconnect()
    assert not client.connected
