from app.security import hash_password, hash_token, new_session_token, verify_password


def test_password_round_trip():
    stored = hash_password("hunter2hunter2")
    assert "hunter2" not in stored
    assert verify_password("hunter2hunter2", stored)
    assert not verify_password("hunter3hunter3", stored)


def test_same_password_gets_different_hashes():
    # Random salts: identical passwords don't produce identical hashes.
    assert hash_password("same-password") != hash_password("same-password")


def test_malformed_stored_hash_is_rejected_not_crashing():
    assert not verify_password("anything", "not-a-real-hash")


def test_session_tokens_are_random_and_stored_hashed():
    a, b = new_session_token(), new_session_token()
    assert a != b and len(a) >= 40
    assert hash_token(a) != a and len(hash_token(a)) == 64
