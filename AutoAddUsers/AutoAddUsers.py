import requests
import json
import sys
import time
from datetime import datetime

# ================= 配置区域 =================
# ✅ 您的真实应用信息
CLIENT_ID = "sample_client_id"
TENANT_ID = "sample_tenant_id"
CLIENT_SECRET = "sample_secret"
SCOPE = "https://graph.microsoft.com/.default"

# 🗺️ 国家代码到【纯安全组】的映射表
# 请确保这些组已经在 Azure AD 中创建（不带邮箱的纯安全组）
COUNTRY_GROUP_MAP = {
    "SG": "SG-Users-Security",
    "MY": "MY-Users-Security",
    "TH": "TH-Users-Security",
    "VN": "VN-Users-Security",
    # 如果有更多国家，请在此处添加
}

# 默认组（可选）：如果用户没有 location 或 location 不匹配，是否加入默认组？
DEFAULT_GROUP_NAME = None
# ===========================================

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    YELLOW = '\033[93m'
    WHITE = '\033[97m'
    GREY = '\033[90m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_color(text, color=Colors.ENDC, bold=False):
    bold_code = Colors.BOLD if bold else ""
    print(f"{bold_code}{color}{text}{Colors.ENDC}")

def get_app_token():
    """获取应用-only 访问令牌"""
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": SCOPE,
        "grant_type": "client_credentials"
    }
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            print_color(f"\n❌ Token Error: {response.status_code}", Colors.RED)
            print(response.text)
            sys.exit(1)
    except Exception as e:
        print_color(f"Network Error: {str(e)}", Colors.RED)
        sys.exit(1)

def get_all_users(token):
    """分页获取所有启用中的用户 (包含 License 信息)"""
    users = []
    url = "https://graph.microsoft.com/v1.0/users"
    headers = {
        "Authorization": f"Bearer {token}",
        "ConsistencyLevel": "eventual"
    }
    # ✅ 关键修改：只获取启用的用户，并包含 assignedLicenses 字段
    params = {
        "$filter": "accountEnabled eq true",
        "$top": 999,
        "$select": "id,userPrincipalName,displayName,usageLocation,assignedLicenses"
    }
    
    print_color("\n📡 Fetching all enabled users from Microsoft Graph...", Colors.CYAN)
    
    while url:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print_color(f"❌ Error fetching users: {response.status_code}", Colors.RED)
            print(response.text)
            return None
            
        data = response.json()
        users.extend(data.get('value', []))
        
        # 处理分页
        url = data.get('@odata.nextLink')
        params = {} # 清除 filter，因为 nextLink 里已经包含了
        
    print_color(f"✅ Found {len(users)} enabled users (Total).", Colors.GREEN)
    return users

def get_group_id(token, group_name):
    """通过组名获取组 ID"""
    url = "https://graph.microsoft.com/v1.0/groups"
    headers = {
        "Authorization": f"Bearer {token}",
        "ConsistencyLevel": "eventual"
    }
    params = {
        "$filter": f"displayName eq '{group_name}'",
        "$select": "id"
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        groups = response.json().get('value', [])
        if groups:
            return groups[0]['id']
        else:
            return None
    return None

def get_group_members(token, group_id):
    """获取组内所有成员的 ID 列表"""
    members = []
    url = f"https://graph.microsoft.com/v1.0/groups/{group_id}/members?$select=id"
    headers = { "Authorization": f"Bearer {token}" }
    
    while url:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            members.extend([m['id'] for m in data['value']])
            url = data.get('@odata.nextLink')
        else:
            break
    return members

def add_user_to_group(token, user_id, group_id, user_name, group_name):
    """将用户添加到组"""
    url = f"https://graph.microsoft.com/v1.0/groups/{group_id}/members/$ref"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "@odata.id": f"https://graph.microsoft.com/v1.0/directoryObjects/{user_id}"
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 204:
        return True, "Success"
    elif response.status_code == 400:
        # 用户可能已经在组里了
        err = response.json()
        if "already exists" in str(err).lower() or "One or more added object references already exist" in str(err):
            return True, "Already Member"
        return False, str(err)
    else:
        return False, response.text

def remove_user_from_group(token, user_id, group_id, user_name, group_name):
    """将用户从组中移除"""
    url = f"https://graph.microsoft.com/v1.0/groups/{group_id}/members/{user_id}/$ref"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.delete(url, headers=headers)
    if response.status_code == 204:
        return True
    else:
        return False

def main():
    start_time = datetime.now()
    print_color("----------------------------------------", Colors.CYAN, bold=True)
    print_color("🤖 Auto Sync Users (Licensed Only)", Colors.CYAN, bold=True)
    print_color(f"⏰ Started at: {start_time.strftime('%H:%M:%S')}", Colors.GREY)
    print_color("----------------------------------------", Colors.CYAN, bold=True)

    # 1. 获取 Token
    token = get_app_token()
    print_color("🔐 Authentication successful.", Colors.GREEN)

    # 2. 预加载所有组 ID
    print_color("\n🔍 Resolving Group IDs...", Colors.CYAN)
    group_cache = {}
    all_target_groups = list(COUNTRY_GROUP_MAP.values())
    if DEFAULT_GROUP_NAME:
        all_target_groups.append(DEFAULT_GROUP_NAME)

    for g_name in set(all_target_groups):
        g_id = get_group_id(token, g_name)
        if g_id:
            group_cache[g_name] = g_id
            print_color(f" ✅ Found group: {g_name}", Colors.GREEN)
        else:
            print_color(f" ⚠️ WARNING: Group '{g_name}' NOT found!", Colors.YELLOW)
            group_cache[g_name] = None

    # 3. 获取所有用户
    all_users = get_all_users(token)
    if not all_users:
        sys.exit(1)

    # 4. ✅ 在 Python 中过滤：只保留有许可证的用户
    print_color("\n⚙️ Filtering users with valid licenses...", Colors.CYAN)
    licensed_users = []
    filtered_count = 0
    
    for user in all_users:
        # 检查 assignedLicenses 是否存在且不为空
        if user.get("assignedLicenses"):
            licensed_users.append(user)
        else:
            filtered_count += 1
            
    print_color(f" ℹ️ Filtered out {filtered_count} users (No License).", Colors.GREY)
    print_color(f" ✅ Processing {len(licensed_users)} licensed users.", Colors.GREEN)

    # 5. 构建目标成员映射表 (Target Mapping)
    # 这是一个字典，Key 是组名，Value 是该组应该包含的用户 ID 列表
    target_memberships = {}
    
    for user in licensed_users:
        u_id = user['id']
        u_loc = user.get('usageLocation')
        u_name = user.get('displayName') or user.get('userPrincipalName')
        u_upn = user.get('userPrincipalName')

        # 确定该用户属于哪个组
        target_group_name = None
        if u_loc and u_loc in COUNTRY_GROUP_MAP:
            target_group_name = COUNTRY_GROUP_MAP[u_loc]
        elif DEFAULT_GROUP_NAME and (not u_loc or u_loc not in COUNTRY_GROUP_MAP):
            target_group_name = DEFAULT_GROUP_NAME

        if target_group_name:
            if target_group_name not in target_memberships:
                target_memberships[target_group_name] = []
            target_memberships[target_group_name].append(u_id)

    # 6. ✅ 核心逻辑：对比并同步 (Sync)
    # 遍历每一个需要维护的组
    stats = {
        "users_added": 0, 
        "users_removed": 0, 
        "errors_add": 0, 
        "errors_remove": 0,
        "skipped_groups": 0
    }

    print_color("\n🔄 Starting Sync Process...", Colors.CYAN)

    for group_name, target_user_ids in target_memberships.items():
        group_id = group_cache.get(group_name)
        if not group_id:
            stats["skipped_groups"] += 1
            continue

        print_color(f"\n📋 Processing Group: {group_name}", Colors.YELLOW)

        # A. 获取组当前的实际成员
        current_member_ids = get_group_members(token, group_id)
        if current_member_ids is None:
            current_member_ids = [] # 如果获取失败，假设为空列表，避免中断

        # B. 计算差集
        # 需要添加的：在目标里，但不在当前组里的
        to_add = set(target_user_ids) - set(current_member_ids)
        # 需要删除的：在当前组里，但不在目标列表里的 (这些人要么没 License 了，要么离职了)
        to_remove = set(current_member_ids) - set(target_user_ids)

        # C. 执行添加
        for user_id in to_add:
            user = next((u for u in licensed_users if u['id'] == user_id), None)
            u_name = user['displayName'] if user else "Unknown"
            success, msg = add_user_to_group(token, user_id, group_id, u_name, group_name)
            if success:
                print_color(f" ➕ ADDED: {u_name}", Colors.GREEN)
                stats["users_added"] += 1
            else:
                print_color(f" ❌ ADD FAIL: {u_name} - {msg}", Colors.RED)
                stats["errors_add"] += 1

        # D. 执行删除
        for user_id in to_remove:
            # 注意：为了显示用户名，我们需要在 all_users (包含所有用户) 中查找，因为 to_remove 可能包含无 License 的用户
            user = next((u for u in all_users if u['id'] == user_id), None)
            u_name = user['displayName'] if user else "Unknown"
            success = remove_user_from_group(token, user_id, group_id, u_name, group_name)
            if success:
                print_color(f" ➖ REMOVED: {u_name} (Unlicensed/Removed)", Colors.YELLOW)
                stats["users_removed"] += 1
            else:
                print_color(f" ❌ DEL FAIL: {u_name}", Colors.RED)
                stats["errors_remove"] += 1

    # 7. 输出总结报告
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print_color("\n" + "="*50, Colors.CYAN, bold=True)
    print_color("📊 EXECUTION SUMMARY", Colors.CYAN, bold=True)
    print_color("="*50, Colors.CYAN, bold=True)
    
    print(f"Total Enabled Users  : {len(all_users)}")
    print(f"Licensed Users         : {len(licensed_users)}")
    print(f"----------------------------------------")
    print_color(f"✅ Users Added        : {stats['users_added']}", Colors.GREEN)
    print_color(f"⏭️ Users Removed      : {stats['users_removed']}", Colors.YELLOW)
    print(f"❌ Add Errors           : {stats['errors_add']}")
    print(f"❌ Remove Errors        : {stats['errors_remove']}")
    print(f"⏱️ Duration             : {duration:.2f} seconds")

    print_color("\n🎉 Automation Complete!", Colors.GREEN, bold=True)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_color("\n\n⛔ Script interrupted by user.", Colors.YELLOW)
        sys.exit(0)
    except Exception as e:
        print_color(f"\n💥 Unhandled Error: {str(e)}", Colors.RED, bold=True)
        sys.exit(1)