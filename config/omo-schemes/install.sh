#!/usr/bin/env bash
# =============================================================================
# OpenCode/OmO 多模型路由配置一键安装脚本
# 支持 macOS / Linux
# 用法: curl -fsSL https://raw.githubusercontent.com/tomzio/agent-config-optimization/main/config/omo-schemes/install.sh | bash
# =============================================================================

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
REPO="tomzio/agent-config-optimization"
BRANCH="main"
SCHEMES_DIR="config/omo-schemes"
INSTALL_DIR="${HOME}/.config/opencode/omo-schemes"
OMO_DIR="${HOME}/.omo"

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# 检查依赖
check_deps() {
    local missing=()
    for cmd in curl python3 git; do
        if ! command -v "$cmd" &>/dev/null; then
            missing+=("$cmd")
        fi
    done
    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "缺少依赖: ${missing[*]}"
        log_info "请先安装: ${missing[*]}"
        exit 1
    fi
}

# 下载方案文件
download_schemes() {
    log_info "下载配置方案..."
    local base_url="https://raw.githubusercontent.com/${REPO}/${BRANCH}/${SCHEMES_DIR}"
    local files=(
        "scheme1-free-first.jsonc"
        "scheme2-plan-first.jsonc"
        "scheme3-free-only.jsonc"
        "switch.py"
        "switch.bat"
        "test_switch.py"
        "validate_config.py"
        "quota-fallback-wrapper.js"
        "preflight-checker.py"
        "proxy-config.example.json"
        "README.md"
    )

    mkdir -p "${INSTALL_DIR}"
    for file in "${files[@]}"; do
        log_info "下载: ${file}"
        curl -fsSL "${base_url}/${file}" -o "${INSTALL_DIR}/${file}" || {
            log_error "下载失败: ${file}"
            exit 1
        }
    done
    log_success "方案文件下载完成: ${INSTALL_DIR}"
}

# 显示方案选择菜单
show_menu() {
    echo
    echo "=========================================="
    echo "  OpenCode/OmO 模型路由配置方案选择"
    echo "=========================================="
    echo
    echo "  1) Scheme 1: 免费优先"
    echo "     免费(opencode) → coding-plan 套餐 → zhipuai GLM → deepseek(末位)"
    echo "     适用: 套餐额度紧张、想最大化免费模型、或免费模型网络更好"
    echo
    echo "  2) Scheme 2: 套餐优先 + Provider 隔离 (推荐)"
    echo "     coding-plan(Ark独占) → deepseek官方(独立配额) → 免费 → zhipuai → deepseek(末位)"
    echo "     适用: 套餐充足、追求稳定、deepseek独立配额避免套餐耗尽影响"
    echo
    echo "  3) Scheme 3: 纯免费 (零成本)"
    echo "     仅用 opencode 免费模型，套餐/按量全不用"
    echo "     适用: 拒绝任何按量调用、压测免费上限、临时额度用尽"
    echo
    echo "  4) 仅下载文件，不切换配置"
    echo
    echo "  q) 退出"
    echo
}

# 从 TTY 读取一行（兼容 curl | bash 场景：管道会占用 stdin）
# 失败（无 TTY / EOF）时返回 1，调用方决定是否降级
read_choice() {
    local prompt="$1"
    local choice=""

    if [ -t 0 ] && [ -r /dev/tty ] 2>/dev/null; then
        # 交互式 TTY：直接读
        if ! read -rp "${prompt}" choice < /dev/tty; then
            return 1
        fi
    else
        # 非 TTY 场景（如 curl | bash 跑到此点）：无 TTY 可读
        return 1
    fi

    printf '%s' "${choice}"
}

# 切换方案
switch_scheme() {
    local scheme_id="$1"
    log_info "切换到方案 ${scheme_id}..."
    
    # 切换前进行配置格式验证
    if ! validate_config "${scheme_id}"; then
        log_error "配置格式验证失败，取消切换"
        return 1
    fi
    
    python3 "${INSTALL_DIR}/switch.py" switch "${scheme_id}"
}

# 配置格式验证 - 调用独立验证脚本
validate_config() {
    local scheme_id="$1"
    local slug
    case "${scheme_id}" in
        1) slug="free-first" ;;
        2) slug="plan-first" ;;
        3) slug="free-only" ;;
        *) log_error "未知方案 ID: ${scheme_id}"; return 1 ;;
    esac
    local scheme_file="${INSTALL_DIR}/scheme${scheme_id}-${slug}.jsonc"

    log_info "验证配置格式: ${scheme_file}"

    if python3 "${INSTALL_DIR}/validate_config.py" "${scheme_file}"; then
        log_success "配置格式验证通过"
        return 0
    else
        log_error "配置格式验证失败"
        return 1
    fi
}

# 验证安装
verify_install() {
    log_info "验证安装..."
    python3 "${INSTALL_DIR}/test_switch.py" || {
        log_error "测试失败，请检查安装"
        exit 1
    }
    log_success "安装验证通过"
}

# 主流程
main() {
    echo
    log_info "OpenCode/OmO 多模型路由配置安装器"
    echo "仓库: https://github.com/${REPO}"
    echo

    check_deps
    download_schemes

    # 创建 omo 目录
    mkdir -p "${OMO_DIR}/backups"

    # 运行测试
    verify_install

    # 交互式选择
    # 兼容 curl | bash 场景：read 时显式从 /dev/tty 取输入，避免被 curl 管道占用
    while true; do
        show_menu
        if ! choice=$(read_choice "请选择方案 [1/2/3/4/q]: "); then
            # 无 TTY 可读（curl | bash 且 TTY 未重定向），降级为「仅下载模式」
            log_warn "未检测到交互终端（curl | bash 场景）"
            log_info "已下载文件到: ${INSTALL_DIR}"
            log_info "请在终端中重新运行安装以选择方案："
            log_info "  bash ${INSTALL_DIR}/install.sh"
            log_info "或手动切换: python3 ${INSTALL_DIR}/switch.py switch <1|2|3>"
            break
        fi
        case "${choice}" in
            1)
                switch_scheme "1"
                break
                ;;
            2)
                switch_scheme "2"
                break
                ;;
            3)
                switch_scheme "3"
                break
                ;;
            4)
                log_info "已下载文件到: ${INSTALL_DIR}"
                log_info "稍后可手动运行: python3 ${INSTALL_DIR}/switch.py switch <1|2|3>"
                break
                ;;
            q|Q)
                log_info "已取消"
                exit 0
                ;;
            *)
                log_warn "无效选择，请重新输入"
                ;;
        esac
    done

    echo
    log_success "安装完成！"
    echo
    echo "后续操作:"
    echo "  1. 重启 OpenCode 使配置生效"
    echo "  2. 验证: 在 OpenCode 中运行 /model 查看模型列表"
    echo "  3. 切换方案: python3 ${INSTALL_DIR}/switch.py switch <1|2|3>"
    echo "  4. 查看文档: ${INSTALL_DIR}/README.md"
    echo
}

main "$@"