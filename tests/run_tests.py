import io, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from modulo_a import parsear_csv

TESTS_DIR = os.path.dirname(__file__)

def run_test(fname, expected_total, expected_correctos, expected_muebles=None):
    path = os.path.join(TESTS_DIR, fname)
    raw = open(path, encoding='utf-8-sig').read()
    r = parsear_csv(io.StringIO(raw))
    assert r['ok'], f"{fname}: error de archivo — {r['error_archivo']}"
    total = len(r['muebles'])
    correctos = sum(1 for m in r['muebles'] if m['estado'] == '✅ CORRECTO')
    assert total == expected_total, f"{fname}: esperado {expected_total} muebles, obtenido {total}\n  Muebles: {[m['name_skp'] for m in r['muebles']]}"
    assert correctos == expected_correctos, (
        f"{fname}: esperado {expected_correctos} CORRECTOS, obtenido {correctos}\n"
        + "\n".join(
            f"  {'✅' if m['estado']=='✅ CORRECTO' else '⚠️'} {m['name_skp']} → name={m['name']}"
            + ("\n    → " + "\n    → ".join(m['avisos']) if m['avisos'] else "")
            for m in r['muebles']
        )
    )
    if expected_muebles:
        for exp in expected_muebles:
            found = next((m for m in r['muebles'] if m['name_skp'] == exp['name_skp']), None)
            assert found, f"{fname}: mueble {exp['name_skp']} no encontrado"
            assert found['estado'] == exp['estado'], f"{fname}: {exp['name_skp']} estado {found['estado']} ≠ {exp['estado']}"
            assert found['name'] == exp['name'], f"{fname}: {exp['name_skp']} name {found['name']} ≠ {exp['name']}"
    # Detalle siempre visible
    for m in r['muebles']:
        estado_sym = '✅' if m['estado'] == '✅ CORRECTO' else '⚠️'
        print(f"  {estado_sym} {m['name_skp']} → name={m['name']}")
        for a in m['avisos']:
            print(f"     → {a}")
    print(f"✅ {fname}: {total} muebles · {correctos} CORRECTOS · {total - correctos} REVISAR\n")

print("=" * 60)
print("TEST 01 - CSV-04_3.csv (reduccion correcta: AVA4722057 -> AVA6022057)")
run_test('CSV-04_3.csv', 1, 1,
    [{'name_skp': 'AVA4722057', 'name': 'AVA6022057', 'estado': '✅ CORRECTO'}])

print("=" * 60)
print("TEST 02 - CSV-04_5.csv (reduccion <300mm, A17)")
run_test('CSV-04_5.csv', 1, 0)

print("=" * 60)
print("TEST 03 - CSV-04_19.csv (HLVV alto fuera de rango, HR correcto)")
run_test('CSV-04_19.csv', 2, 1)

print("=" * 60)
print("TEST 04 - CSV-04_20.csv (HLVV y HR con errores)")
run_test('CSV-04_20.csv', 2, 0)

print("=" * 60)
print("TEST 05 - CSV-04_21.csv (HR no admite reduccion, A16a)")
run_test('CSV-04_21.csv', 2, 1)

print("=" * 60)
print("TEST 06 - CSV-04_23.csv (9 muebles, 2 correctos: HH1908035 y HR60V57)")
run_test('CSV-04_23.csv', 9, 2,
    [{'name_skp': 'HH1908035', 'name': 'HH1908035', 'estado': '✅ CORRECTO'},
     {'name_skp': 'HR60V57', 'name': 'HR60V57', 'estado': '✅ CORRECTO'}])

print("=" * 60)
print("TEST 07 - CSV-05_1.csv (9 muebles, 2 correctos)")
run_test('CSV-05_1.csv', 9, 2)

print("=" * 60)
print("TEST 08 - CSV_121_muebles.csv (121 muebles todos CORRECTOS)")
run_test('CSV_121_muebles.csv', 121, 121)

print("=" * 60)
print("TODOS LOS TESTS PASARON.")
