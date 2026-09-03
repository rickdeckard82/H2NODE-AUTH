from app.services.password import make_nt_hash, make_ssha512, verify_ssha512


def test_ssha512_roundtrip():
    h = make_ssha512("Str0ngPass!x12")
    assert verify_ssha512("Str0ngPass!x12", h)
    assert not verify_ssha512("outra", h)
    # salt aleatório => hashes diferentes para a mesma senha
    assert make_ssha512("x") != make_ssha512("x")


def test_nt_hash_known_vectors():
    # vetores clássicos do NT hash (MD4 do UTF-16LE)
    assert make_nt_hash("") == "31d6cfe0d16ae931b73c59d7e0c089c0"
    assert make_nt_hash("password") == "8846f7eaee8fb117ad06bdd830b7586c"
    assert make_nt_hash("test") == "0cb6948805f797bf2a82807973b89537"


def test_nt_hash_is_stable_and_unsalted():
    assert make_nt_hash("ehsv2@(Neolink)#") == make_nt_hash("ehsv2@(Neolink)#")
    assert len(make_nt_hash("qualquer")) == 32
