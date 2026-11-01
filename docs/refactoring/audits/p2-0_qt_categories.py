import os, re

BIN = r"E:\Dev\Work_temp\SupervertalerPortable\recon-p20\unpacked\python-embed\Lib\site-packages\PyQt6\Qt6\bin"
SP = r"E:\Dev\Work_temp\SupervertalerPortable\recon-p20\unpacked\python-embed\Lib\site-packages"

cats = {
    "Quick/QML stack (Qt6Quick*, Qt6Qml*, ShaderTools, StateMachine, SensorsQuick)": r"^Qt6(Quick|Qml|ShaderTools|StateMachine|SensorsQuick)",
    "Qt Designer (Qt6Designer)": r"^Qt6Designer",
    "Pdf (Qt6Pdf*)": r"^Qt6Pdf",
    "Multimedia+ffmpeg (Qt6Multimedia*, SpatialAudio, av*, sw*)": r"^(Qt6(Multimedia|SpatialAudio)|av|sw)",
    "Connectivity/IoT (Bluetooth, Nfc, Positioning, SerialPort, RemoteObjects, WebSockets, TextToSpeech, Sensors, Scxml?)": r"^Qt6(Bluetooth|Nfc|Positioning|SerialPort|RemoteObjects|WebSockets|TextToSpeech|Sensors$|Scxml)",
    "Test (Qt6Test, Qt6QuickTest)": r"^Qt6(Quick)?Test$",
    "Software OpenGL fallback (opengl32sw)": r"^opengl32sw",
    "Help/Sql/DBus/Xml/PrintSupport/Svg/Network (KEEP-candidates, need check)": r"^Qt6(Help|Sql|DBus|Xml|PrintSupport|Svg|Network)$",
    "Core+Gui+Widgets+OpenGL (required)": r"^Qt6(Core|Gui|Widgets|OpenGL)$",
    "MSVC runtime + d3dcompiler (keep)": r"^(msvcp140|vccorlib140|concrt140|d3dcompiler|vcruntime)",
}
sums = {k: 0.0 for k in cats}
unmatched = []
for f in os.listdir(BIN):
    p = os.path.join(BIN, f)
    s = os.path.getsize(p) / 1048576
    for k, pat in cats.items():
        if re.match(pat, f):
            sums[k] += s
            break
    else:
        unmatched.append((f, s))
for k, v in sums.items():
    print(f"{v:8.1f} MB  {k}")
print("\nUNMATCHED:")
for f, s in sorted(unmatched, key=lambda x: -x[1]):
    print(f"{s:8.1f} MB  {f}")

# plugin categories
PL = os.path.join(SP, "PyQt6", "Qt6", "plugins")
def dsize(p):
    t = 0
    for dp, dn, fn in os.walk(p):
        for f in fn:
            t += os.path.getsize(os.path.join(dp, f))
    return t / 1048576
print("\nPLUGINS (all):")
for d in sorted(os.listdir(PL)):
    print(f"{dsize(os.path.join(PL, d)):8.1f} MB  {d}")

# other site-packages dev junk
for name in ("pip", "pytest", "_pytest", "pyflakes", "pygments", "iniconfig", "pluggy", "chardet"):
    p = os.path.join(SP, name)
    if os.path.isdir(p):
        print(f"{dsize(p):8.1f} MB  site-packages/{name}")
print(f"{os.path.getsize(os.path.join(SP,'..','..','get-pip.py'))/1048576:8.1f} MB  python-embed/get-pip.py")

# PyQt6 non-Qt6 payload: .pyi stubs + bindings + unused .pyd modules
Q6 = os.path.join(SP, "PyQt6")
pyi = sum(os.path.getsize(os.path.join(dp, f)) for dp, dn, fn in os.walk(Q6) for f in fn if f.endswith(".pyi")) / 1048576
print(f"{pyi:8.1f} MB  PyQt6 .pyi stubs")
unused_pyd = ["QtQuick", "QtQml", "QtNetwork", "QtSql", "QtDesigner", "QtPdf", "QtPdfWidgets", "QtMultimedia",
              "QtMultimediaWidgets", "QtBluetooth", "QtNfc", "QtPositioning", "QtSerialPort", "QtRemoteObjects",
              "QtWebSockets", "QtTextToSpeech", "QtSensors", "QtTest", "QtStateMachine", "QtHelp", "QtDBus",
              "QAxContainer", "QtOpenGL", "QtOpenGLWidgets", "QtQuickWidgets", "QtQuick3D", "QtSpatialAudio",
              "QtSvg", "QtSvgWidgets", "QtXml", "QtWebChannel"]
tot = 0
for name in unused_pyd:
    p = os.path.join(Q6, name + ".pyd")
    if os.path.exists(p):
        s = os.path.getsize(p) / 1048576
        tot += s
print(f"{tot:8.1f} MB  PyQt6 *.pyd for modules not imported by product (name-list)")
bindings = dsize(os.path.join(Q6, "bindings"))
print(f"{bindings:8.1f} MB  PyQt6/bindings (build-time .toml)")
