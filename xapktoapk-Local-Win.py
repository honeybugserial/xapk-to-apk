import json
import os
import platform
import shutil
import sys
import re
import time
from zipfile import ZipFile

from subprocess import call, STDOUT
try:
    from subprocess import DEVNULL
except ImportError:
    import os
    DEVNULL = open(os.devnull, 'wb')

const_dir_tmp = "tmp_xapktoapk"
const_file_target_file = "target"
const_ext_apk = ".apk"
const_ext_xapk = ".xapk"
const_ext_zip = ".zip"

const_file_xapk_manifest = "manifest.json"
const_file_xapk_manifest_key_package_name = "package_name"

const_prefix_apk_split_type_config = "config"
const_suffix_apk_split_type_dpi = "dpi"
const_values_apk_split_type_arch = ["arm64_v8a", "armeabi_v7a", "armeabi", "x86", "x86_64"]

const_split_apk_type_main = "main"
const_split_apk_type_arch = "arch"
const_split_apk_type_dpi = "dpi"
const_split_apk_type_locale = "locale"

const_apk_file_apktool_config = 'apktool.yml'
const_apk_dir_lib = 'lib'

const_sign_config_properties_file = 'xapktoapk.sign.properties'


def get_local_tool(tool_name):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    tool_path = os.path.join(script_dir, 'tools', tool_name)
    if not os.path.exists(tool_path):
        raise FileNotFoundError(f"Required tool '{tool_name}' not found in tools/ directory.")
    return tool_path


def execute_command_subprocess(command_tokens_list):
    print(f"[DEBUG] Running command: {' '.join(command_tokens_list)}")
    return call(command_tokens_list)


def print_help():
    print("\nXapkToApk is a tool that converts .xapk file into .apk file")
    print("Usage: python xapktoapk.py PATH_TO_FILE.xapk\n")


def get_param_xapk_file_name():
    return sys.argv[1]


def get_param_xapk_abs_path():
    return os.path.abspath(get_param_xapk_file_name())


def check_sys_args():
    return len(sys.argv) == 2 and sys.argv[1].endswith(const_ext_xapk) and os.path.exists(get_param_xapk_abs_path())


def create_tmp_dir(working_dir):
    path_dir_tmp = os.path.abspath(os.path.join(working_dir, const_dir_tmp))
    if os.path.exists(path_dir_tmp):
        shutil.rmtree(path_dir_tmp)
    os.mkdir(path_dir_tmp)
    return path_dir_tmp


def file_split_name_and_extension(file_path):
    return os.path.splitext(file_path)


def determine_split_type_by_apk_file_name(apk_file_name, xapk_package_name):
    try:
        if (xapk_package_name + const_ext_apk) == apk_file_name or 'base.apk' == apk_file_name:
            return const_split_apk_type_main
        elif apk_file_name.startswith(const_prefix_apk_split_type_config):
            clear_file_name = os.path.splitext(apk_file_name)[0]
            config_name = str(clear_file_name.split('.')[1])
            if config_name.endswith(const_suffix_apk_split_type_dpi):
                return const_split_apk_type_dpi
            elif config_name in const_values_apk_split_type_arch:
                return const_split_apk_type_arch
            else:
                return const_split_apk_type_locale
        else:
            return const_split_apk_type_locale
    except:
        return None


def get_apks_of_type(target_apks, type):
    return [entry for entry in target_apks.values() if entry['apk_split_type'] == type]


def get_main_apk(target_apks):
    return get_apks_of_type(target_apks, const_split_apk_type_main)[0]


def unpack_apk(path_dir_tmp, apk_file, number_current, number_total):
    print(f'[*] unpacking {number_current} of {number_total}')
    os.chdir(path_dir_tmp)
    apktool = get_local_tool('apktool.bat')
    rc = execute_command_subprocess([apktool, 'd', '-s', apk_file])
    if rc != 0:
        raise Exception(f"failed to unpack {apk_file}")
    os.remove(os.path.join(path_dir_tmp, apk_file))


def pack_apk(path_dir_tmp, main_apk_dir):
    print('[*] repack apk')
    os.chdir(path_dir_tmp)
    apktool = get_local_tool('apktool.bat')
    print(f"[DEBUG] Running: {apktool} b {main_apk_dir}")
    rc = execute_command_subprocess([apktool, 'b', main_apk_dir])
    print(f"[DEBUG] apktool exit code: {rc}")
    if rc != 0:
        raise Exception("failed to pack apk")
    built_apk_path = os.path.join(path_dir_tmp, main_apk_dir, 'dist', f"{os.path.basename(main_apk_dir)}{const_ext_apk}")
    if not os.path.exists(built_apk_path):
        raise Exception("result apk not found")
    target_apk_path = os.path.join(path_dir_tmp, f"{const_file_target_file}{const_ext_apk}")
    if os.path.exists(target_apk_path):
        os.remove(target_apk_path)
    shutil.copy(built_apk_path, target_apk_path)


def update_main_manifest_file(path_main_apk):
    path_manifest = os.path.join(path_main_apk, 'AndroidManifest.xml')
    if not os.path.exists(path_manifest):
        print("[WARN] Manifest file not found, skipping cleanup.")
        return

    print("[*] Cleaning AndroidManifest.xml...")
    with open(path_manifest, 'r', encoding='utf-8') as f:
        data = f.read()

    data = re.sub(r'\s*android:isSplitRequired="true"', '', data)
    data = re.sub(r'\s*android:requiredSplitTypes="[^"]*"', '', data)
    data = re.sub(r'\s*android:splitTypes="[^"]*"', '', data)
    data = re.sub(r'android:value="STAMP_TYPE_DISTRIBUTION_APK"', 'android:value="STAMP_TYPE_STANDALONE_APK"', data)
    data = re.sub(r'<meta-data[^>]*android:name="com\\.android\\.vending\\.splits\\.required"[^>]*/>', '', data)
    data = re.sub(r'<meta-data[^>]*android:name="com\\.android\\.vending\\.splits"[^>]*/>', '', data)

    with open(path_manifest, 'w', encoding='utf-8') as f:
        f.write(data)

    print("[*] Manifest cleaned successfully.")


def zipalign_apk(path_dir_tmp):
    print('[*] zipalign apk')
    os.chdir(path_dir_tmp)
    zipalign = get_local_tool('zipalign.exe')
    input_apk = os.path.join(path_dir_tmp, f"{const_file_target_file}{const_ext_apk}")
    aligned_apk = os.path.join(path_dir_tmp, f"aligned_{const_file_target_file}{const_ext_apk}")
    if os.path.exists(aligned_apk):
        os.remove(aligned_apk)
    rc = execute_command_subprocess([zipalign, '-p', '-f', '4', input_apk, aligned_apk])
    if rc != 0 or not os.path.exists(aligned_apk):
        raise Exception("failed to zipalign apk")
    os.remove(input_apk)
    shutil.move(aligned_apk, input_apk)


def sign_apk(path_dir_tmp, sign_config):
    apk_file = os.path.join(path_dir_tmp, f"{const_file_target_file}{const_ext_apk}")
    if not os.path.exists(apk_file):
        raise Exception("result apk not found")
    print('[*] signing apk')
    os.chdir(path_dir_tmp)
    apksigner = get_local_tool('apksigner.bat')
    rc = execute_command_subprocess([
        apksigner, 'sign',
        '--ks', os.path.expanduser(sign_config['sign.keystore.file']),
        '--ks-pass', f"pass:{sign_config['sign.keystore.password']}",
        '--ks-key-alias', sign_config['sign.key.alias'],
        '--key-pass', f"pass:{sign_config['sign.key.password']}",
        apk_file
    ])
    if rc != 0:
        raise Exception("failed to sign apk")


def load_sign_properties():
    for base in [os.getcwd(), os.path.expanduser('~')]:
        path = os.path.join(base, const_sign_config_properties_file)
        if os.path.exists(path):
            with open(path, 'r', encoding='UTF-8') as f:
                lines = f.readlines()
            props = {}
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    props[k.strip()] = v.strip()
            if props.get('sign.enabled', '').lower() == 'true':
                return props
    return None


def ensure_local_debug_keystore():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    tools_dir = os.path.join(script_dir, "tools")
    os.makedirs(tools_dir, exist_ok=True)
    keystore_path = os.path.join(tools_dir, "debug.keystore")
    props_path = os.path.join(script_dir, const_sign_config_properties_file)

    if not os.path.exists(keystore_path):
        print("[*] Generating debug keystore...")
        rc = call([
            "keytool", "-genkey", "-v",
            "-keystore", keystore_path,
            "-storepass", "android",
            "-alias", "androiddebugkey",
            "-keyalg", "RSA", "-keysize", "2048",
            "-validity", "10000",
            "-keypass", "android",
            "-dname", "CN=Android Debug,O=Android,C=US"
        ], stdout=DEVNULL, stderr=STDOUT)
        if rc != 0:
            raise Exception("Failed to generate debug keystore.")

    if not os.path.exists(props_path):
        print("[*] Creating default signing config...")
        with open(props_path, "w", encoding="utf-8") as f:
            f.write(f"""sign.enabled=true
sign.keystore.file={keystore_path}
sign.keystore.password=android
sign.key.alias=androiddebugkey
sign.key.password=android
""")


def main():
    if not check_sys_args():
        print_help()
        sys.exit(1)

    try:
        get_local_tool('apktool.bat')
        get_local_tool('zipalign.exe')
        get_local_tool('apksigner.bat')
    except FileNotFoundError as e:
        print(e)
        sys.exit(2)

    ensure_local_debug_keystore()
    sign_config = load_sign_properties()

    xapk_file = get_param_xapk_abs_path()
    base_name = os.path.splitext(os.path.basename(xapk_file))[0]
    cwd = os.getcwd()
    tmp_dir = create_tmp_dir(cwd)

    tmp_xapk = os.path.join(tmp_dir, f"{const_file_target_file}{const_ext_xapk}")
    tmp_zip = os.path.join(tmp_dir, f"{const_file_target_file}{const_ext_zip}")

    shutil.copy(xapk_file, tmp_xapk)
    os.rename(tmp_xapk, tmp_zip)

    print('[*] unpacking xapk')
    with ZipFile(tmp_zip, 'r') as zip_ref:
        zip_ref.extractall(tmp_dir)
    os.remove(tmp_zip)

    manifest_path = os.path.join(tmp_dir, const_file_xapk_manifest)
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    package_name = manifest[const_file_xapk_manifest_key_package_name]

    apk_files = [f for f in os.listdir(tmp_dir) if f.endswith(const_ext_apk)]
    target_apks = {}
    for apk_file in apk_files:
        apk_type = determine_split_type_by_apk_file_name(apk_file, package_name)
        if apk_type is None:
            raise Exception(f"Cannot determine split type for {apk_file}")
        target_apks[apk_file] = {
            'apk_file_name': apk_file,
            'apk_file_path': os.path.join(tmp_dir, apk_file),
            'apk_dir_name': os.path.splitext(apk_file)[0],
            'apk_dir_path': os.path.join(tmp_dir, os.path.splitext(apk_file)[0]),
            'apk_split_type': apk_type
        }

    print(f'[*] {len(apk_files)} APK parts found')

    for i, key in enumerate(target_apks):
        unpack_apk(tmp_dir, target_apks[key]['apk_file_name'], i + 1, len(target_apks))

    main_apk = get_main_apk(target_apks)

    update_main_manifest_file(main_apk['apk_dir_path'])
    pack_apk(tmp_dir, main_apk['apk_dir_path'])
    zipalign_apk(tmp_dir)
    if sign_config:
        sign_apk(tmp_dir, sign_config)

    final_apk = os.path.join(tmp_dir, f"{const_file_target_file}{const_ext_apk}")
    output_apk = os.path.join(cwd, f"{base_name}{const_ext_apk}")
    shutil.copy(final_apk, output_apk)

    for attempt in range(5):
        try:
            shutil.rmtree(tmp_dir)
            break
        except PermissionError:
            print(f"[WARN] Attempt {attempt + 1}: Temp dir locked. Retrying in 1s...")
            time.sleep(1)
    else:
        print(f"[WARN] Cleanup failed after 5 attempts. Please delete '{tmp_dir}' manually.")

    print("\n" + "*" * 100)
    print(f"[*] Done! APK saved to:\n    {output_apk}")
    print("*" * 100 + "\n")


if __name__ == '__main__':
    main()
