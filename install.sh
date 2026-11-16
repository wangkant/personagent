#!/bin/sh
# personagent installer for macOS and Linux. Nothing needs to be installed first:
#
#   curl -LsSf https://raw.githubusercontent.com/wangkant/personagent/main/install.sh | sh
#
# It fetches uv (which brings its own Python), installs personagent with it and
# opens the app. Run it again to update.
#
# Settings, as environment variables:
#   PERSONAGENT_VERSION         install this version instead of the newest
#   PERSONAGENT_MIRROR          auto (default), cn (always use the mirrors), off (never)
#   PERSONAGENT_NO_START        1: do not open the app at the end
#   PERSONAGENT_NO_SHORTCUT     1: no launcher (macOS desktop, Linux application menu)
#   PERSONAGENT_NO_MODIFY_PATH  1: leave the shell's PATH as it is
#   PERSONAGENT_UV_DIR          where uv goes when it is not installed yet
set -eu

INDEX_MIRROR_1="https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple"
INDEX_MIRROR_2="https://mirrors.aliyun.com/pypi/simple"
PYTHON_MIRROR="https://registry.npmmirror.com/-/binary/python-build-standalone"
PYTHON_VERSION="3.12"

say() {
    # One sentence in the system's language: English, or Chinese.
    case "${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}" in
        zh*) printf '%s\n' "${2:-$1}" ;;
        *) printf '%s\n' "$1" ;;
    esac
}

fail() {
    say "$@" >&2
    exit 1
}

have() {
    command -v "$1" >/dev/null 2>&1
}

fetch() {
    # fetch URL FILE
    if have curl; then
        curl -fsSL --connect-timeout 15 --retry 2 -o "$2" "$1"
    else
        wget -q -T 30 -O "$2" "$1"
    fi
}

reachable() {
    if have curl; then
        curl -fsSIL --max-time 8 -o /dev/null "$1" 2>/dev/null
    else
        wget -q -T 8 --spider "$1" 2>/dev/null
    fi
}

wheel_pattern() {
    # The part of a uv wheel's file name that names this system, as a grep pattern.
    os=$(uname -s)
    arch=$(uname -m)
    case "$os" in
        Darwin)
            case "$arch" in
                arm64 | aarch64) echo 'macosx_[0-9_]*_arm64' ;;
                x86_64) echo 'macosx_[0-9_]*_x86_64' ;;
                *) return 1 ;;
            esac ;;
        Linux)
            musl=""
            if ls /lib/ld-musl-* >/dev/null 2>&1 || (ldd --version 2>&1 | grep -qi musl); then musl=1; fi
            case "$arch" in
                x86_64 | amd64)
                    if [ -n "$musl" ]; then echo 'musllinux_[0-9_]*_x86_64'; else echo 'manylinux[a-z0-9_.]*_x86_64'; fi ;;
                # One aarch64 wheel carries both the oldest glibc tag and the musl tag.
                aarch64 | arm64) echo '[a-z0-9_.]*musllinux_[0-9_]*_aarch64' ;;
                *) return 1 ;;
            esac ;;
        *) return 1 ;;
    esac
}

find_wheel() {
    # find_wheel INDEX PATTERN PAGE: the newest matching uv wheel, as "URL SHA256".
    base="${1%/}/uv/"
    fetch "$base" "$3" || return 1
    pick_wheel "$base" "$2" "$3"
}

pick_wheel() {
    # pick_wheel BASE PATTERN PAGE: the same, from an index page already on disk.
    line=$(grep -o "href=\"[^\"]*uv-[0-9][0-9.]*-py3-none-$2\.whl[^\"]*\"" "$3" |
        sed 's/^href="//; s/"$//' |
        awk '{ v = $0; sub(/.*\/uv-/, "", v); sub(/^uv-/, "", v); sub(/-py3.*/, "", v); print v " " $0 }' |
        sort -t. -k1,1n -k2,2n -k3,3n | tail -n 1 | cut -d' ' -f2-)
    [ -n "$line" ] || return 1
    href=${line%%#*}
    sum=""
    case "$line" in *"#sha256="*) sum=${line##*#sha256=} ;; esac
    case "$href" in
        http://* | https://*) : ;;
        *) href="$1$href" ;;
    esac
    echo "$href $sum"
}

checksum_ok() {
    # checksum_ok FILE SHA256; true as well when nothing here can compute one.
    [ -n "$2" ] || return 0
    if have sha256sum; then
        actual=$(sha256sum "$1" | cut -d' ' -f1)
    elif have shasum; then
        actual=$(shasum -a 256 "$1" | cut -d' ' -f1)
    else
        return 0
    fi
    [ "$actual" = "$2" ]
}

unpack_uv() {
    # unpack_uv WHEEL DIR: a wheel is a zip; uv and uvx sit under *.data/scripts/.
    out="$2/.personagent-unpack"
    rm -rf "$out"
    mkdir -p "$out"
    if have unzip; then
        unzip -q -o "$1" '*.data/scripts/*' -d "$out" || return 1
    elif have bsdtar; then
        bsdtar -xf "$1" -C "$out" || return 1
    elif [ "$(uname -s)" = Darwin ]; then
        tar -xf "$1" -C "$out" || return 1
    elif have python3; then
        python3 -m zipfile -e "$1" "$out" || return 1
    else
        return 1
    fi
    found=""
    for name in uv uvx; do
        for file in "$out"/*.data/scripts/"$name"; do
            [ -f "$file" ] || continue
            cp "$file" "$2/$name"
            chmod +x "$2/$name"
            [ "$name" = uv ] && found=1
        done
    done
    rm -rf "$out"
    [ -n "$found" ]
}

install_uv() {
    # install_uv DIR INDEX...: uv from a package index into DIR.
    dir=$1
    shift
    pattern=$(wheel_pattern) || return 1
    mkdir -p "$dir"
    for index in "$@"; do
        if found=$(find_wheel "$index" "$pattern" "$TMP/index.html"); then
            url=${found% *}
            sum=${found#* }
            if fetch "$url" "$TMP/uv.whl" && checksum_ok "$TMP/uv.whl" "$sum" \
                && unpack_uv "$TMP/uv.whl" "$dir"; then
                return 0
            fi
        fi
    done
    # No unzip here, or no index answered: Astral's own installer needs only tar.
    if fetch "https://astral.sh/uv/install.sh" "$TMP/uv-install.sh"; then
        UV_UNMANAGED_INSTALL="$dir" sh "$TMP/uv-install.sh" >/dev/null 2>&1 && [ -x "$dir/uv" ] && return 0
    fi
    return 1
}

uv_recent() {
    # uv_recent EXE: true for uv 0.8 or later.
    version=$("$1" --version 2>/dev/null | sed -n 's/^uv \([0-9][0-9]*\)\.\([0-9][0-9]*\).*/\1 \2/p')
    [ -n "$version" ] || return 1
    major=${version% *}
    minor=${version#* }
    [ "$major" -gt 0 ] || [ "$minor" -ge 8 ]
}

foreign_copy() {
    # foreign_copy UV: a personagent in uv's executable folder that uv did not put there.
    bin=$("$1" tool dir --bin 2>/dev/null) || return 1
    [ -e "$bin/personagent" ] || return 1
    ! "$1" tool list 2>/dev/null | grep -q '^personagent '
}

make_launcher() {
    # A way to open it without a terminal: a desktop file on macOS, a menu entry on Linux.
    exe=$1
    case "$(uname -s)" in
        Darwin)
            folder="${PERSONAGENT_SHORTCUT_DIR:-$HOME/Desktop}"
            [ -d "$folder" ] || return 0
            printf '#!/bin/sh\nexec "%s" start\n' "$exe" >"$folder/personagent.command"
            chmod +x "$folder/personagent.command" ;;
        Linux)
            folder="${PERSONAGENT_SHORTCUT_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/applications}"
            mkdir -p "$folder" 2>/dev/null || return 0
            printf '[Desktop Entry]\nType=Application\nName=personagent\nExec="%s" start\nTerminal=true\nCategories=Network;Chat;\n' \
                "$exe" >"$folder/personagent.desktop" ;;
    esac
}

main() {
    printf '\n  personagent\n\n'
    have curl || have wget || fail "curl or wget is needed to download personagent." "下载 personagent 需要 curl 或 wget。"
    wheel_pattern >/dev/null || fail "personagent has no installer for this system ($(uname -s) $(uname -m))." \
        "此安装脚本不支持当前系统（$(uname -s) $(uname -m)）。"

    TMP=$(mktemp -d 2>/dev/null || mktemp -d -t personagent)
    trap 'rm -rf "$TMP"' EXIT INT TERM

    mode=${PERSONAGENT_MIRROR:-auto}
    index_mirror=""
    python_mirror=""
    case "$mode" in
        cn) index_mirror=1; python_mirror=1 ;;
        off) : ;;
        *)
            mode=auto
            say "Checking the network..." "正在检查网络..."
            reachable "https://pypi.org/simple/personagent/" || index_mirror=1
            # A release asset, as the Python download is one.
            reachable "https://github.com/astral-sh/python-build-standalone/releases/download/20241016/SHA256SUMS" || python_mirror=1
            if [ -n "$index_mirror$python_mirror" ]; then
                say "PyPI or GitHub is slow to reach from here; using mirrors in mainland China." \
                    "PyPI 或 GitHub 访问不畅，将改用中国大陆的镜像。"
            fi ;;
    esac

    # An older uv lacks `uv tool` or `--default-index`; it would fail and read as a network fault.
    if have uv && uv_recent "$(command -v uv)"; then
        uv=$(command -v uv)
    else
        uv_dir="${PERSONAGENT_UV_DIR:-$HOME/.local/bin}"
        uv="$uv_dir/uv"
        if [ ! -x "$uv" ]; then
            say "Fetching uv, which installs Python and personagent..." "正在获取 uv（用于安装 Python 和 personagent）..."
            if [ -n "$index_mirror" ]; then
                install_uv "$uv_dir" "$INDEX_MIRROR_1" "$INDEX_MIRROR_2" "https://pypi.org/simple"
            else
                install_uv "$uv_dir" "https://pypi.org/simple" "$INDEX_MIRROR_1" "$INDEX_MIRROR_2"
            fi || fail "uv could not be downloaded. Check the network connection and proxy settings, then run this again." \
                "uv 下载失败。请检查网络连接和代理设置，然后重新运行。"
        fi
    fi

    spec="personagent"
    [ -z "${PERSONAGENT_VERSION:-}" ] || spec="personagent==$PERSONAGENT_VERSION"
    [ -z "${PERSONAGENT_PACKAGE:-}" ] || spec="$PERSONAGENT_PACKAGE"

    say "Installing personagent. The first time this downloads Python and takes a few minutes..." \
        "正在安装 personagent。首次安装需下载 Python，约需几分钟..."
    force=""
    if foreign_copy "$uv"; then
        force="--force"
        say "Replacing the personagent that was installed another way (pip or pipx)." \
            "正在替换以其他方式（pip 或 pipx）安装的 personagent。"
    fi
    run_install() {
        # run_install USE_INDEX_MIRROR USE_PYTHON_MIRROR
        set -- "$1" "$2" tool install --python "$PYTHON_VERSION" --upgrade $force
        use_index=$1
        use_python=$2
        shift 2
        # On the command line, so that later upgrades of the tool use it too.
        if [ -n "$use_index" ] && [ -z "${UV_DEFAULT_INDEX:-}" ]; then set -- "$@" --default-index "$INDEX_MIRROR_1"; fi
        if [ -n "$use_python" ] && [ -z "${UV_PYTHON_INSTALL_MIRROR:-}" ]; then
            UV_PYTHON_INSTALL_MIRROR="$PYTHON_MIRROR" "$uv" "$@" "$spec"
        else
            "$uv" "$@" "$spec"
        fi
    }
    if ! run_install "$index_mirror" "$python_mirror"; then
        if [ "$mode" = auto ] && { [ -z "$index_mirror" ] || [ -z "$python_mirror" ]; }; then
            say "That did not work; trying again through mirrors in mainland China..." "安装未成功，改用中国大陆的镜像重试..."
            run_install 1 1 || fail "personagent could not be installed. Check the network connection and proxy settings, then run this again." \
                "personagent 未能安装。请检查网络连接和代理设置，然后重新运行。"
        else
            fail "personagent could not be installed. Check the network connection and proxy settings, then run this again." \
                "personagent 未能安装。请检查网络连接和代理设置，然后重新运行。"
        fi
    fi

    bin=$("$uv" tool dir --bin)
    exe="$bin/personagent"
    [ -x "$exe" ] || fail "personagent was installed, but $exe is missing."
    # So that `personagent` and `uv` work in terminals opened from now on.
    [ -n "${PERSONAGENT_NO_MODIFY_PATH:-}" ] || "$uv" tool update-shell >/dev/null 2>&1 || true
    [ -n "${PERSONAGENT_NO_SHORTCUT:-}" ] || make_launcher "$exe" || true

    printf '\n'
    say "personagent is installed." "personagent 已安装。"
    say "  Open it:    run \`personagent\` in a new terminal" "  打开：在新终端中运行 personagent"
    say "  Update it:  the App view of the page, or run this installer again" "  更新：在页面的「应用」视图中更新，或重新运行此安装命令"
    say "  Remove it:  uv tool uninstall personagent" "  卸载：uv tool uninstall personagent"
    printf '\n'

    [ -z "${PERSONAGENT_NO_START:-}" ] || return 0
    if [ "$(uname -s)" = Linux ] && [ -z "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
        say "No display here: \`$exe up\` starts the service and its platforms; \`$exe start --no-browser\` prints the page's link." \
            "此处没有图形界面：运行 $exe up 可启动服务及已连接的平台；运行 $exe start --no-browser 可获得页面链接。"
        return 0
    fi
    # Under `curl | sh` the script itself is on stdin; the app wants the terminal.
    if [ -r /dev/tty ]; then
        say "Opening personagent..." "正在打开 personagent..."
        rm -rf "$TMP"
        exec "$exe" start </dev/tty
    fi
}

main "$@"
