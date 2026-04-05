from core.security import verify_password

# The hash we put in the DB
db_hash = "$2b$12$jcEzfOyhfrCNyEAwx/8KPOhJ2vgDh7QZ5xtPdVswAYd5WHNFkaEMu"
password = "risc2026"

print(f"Testing password '{password}' against hash '{db_hash}'...")
try:
    if verify_password(password, db_hash):
        print("SUCCESS: Password verified!")
    else:
        print("FAILURE: Password did not match.")
except Exception as e:
    print(f"ERROR: {e}")
