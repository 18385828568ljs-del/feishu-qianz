"""
外部签名表单 API 路由
"""
import json
import uuid
import os
import requests
import time
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, SignForm

router = APIRouter(
    prefix="/api/form", 
    tags=["表单"],
    responses={404: {"description": "表单不存在"}}
)

# 从环境变量获取飞书应用配置
APP_ID = os.getenv("APP_ID", "")
APP_SECRET = os.getenv("APP_SECRET", "")


# ==================== 字段类型映射 ====================
# 飞书字段类型代码 -> 表单输入类型
FIELD_TYPE_MAP = {
    1: "text",        # 文本
    2: "number",      # 数字
    3: "select",      # 单选
    4: "multiselect", # 多选
    5: "date",        # 日期
    7: "checkbox",    # 复选框
    13: "phone",      # 电话
    15: "url",        # URL
    17: "attachment", # 附件（签名）
    19: "email",      # 邮箱
}

# 不支持的字段类型（人员、公式等）
UNSUPPORTED_FIELD_TYPES = {11, 20, 21, 22}


# ==================== 请求/响应模型 ====================

class FieldConfig(BaseModel):
    """表单字段配置"""
    field_id: str                      # 飞书字段ID
    field_name: str = ""               # 飞书原始字段名
    label: str                         # 表单显示标签
    type: int = 1                      # 飞书字段类型代码
    input_type: str = "text"           # 表单输入类型
    required: bool = False             # 是否必填
    options: List[str] = []            # 单选/多选的选项
    placeholder: str = ""              # 输入提示


class CreateFormRequest(BaseModel):
    name: str
    description: Optional[str] = None
    app_token: str
    table_id: str
    signature_field_id: Optional[str] = None  # 签名字段（可选）
    fields: Optional[List[FieldConfig]] = None  # 表单字段列表
    extra_fields: Optional[List[FieldConfig]] = None  # 兼容旧版
    created_by: Optional[str] = None
    session_id: Optional[str] = None
    record_index: Optional[int] = 1  # 记录条索引，默认为1
    show_data: Optional[bool] = False  # 是否在表单中显示关联记录的数据


class FormConfigResponse(BaseModel):
    form_id: str
    name: str
    description: Optional[str]
    fields: List[dict]
    signature_required: bool = False


# ==================== 辅助函数 ====================

def generate_form_id() -> str:
    """生成短表单ID"""
    return uuid.uuid4().hex[:8]


def log_to_file(msg):
    """记录日志到文件"""
    try:
        with open("debug.log", "a", encoding="utf-8") as f:
            f.write(f"{datetime.now()} - {msg}\n")
    except:
        pass


def get_app_access_token() -> str:
    """获取飞书应用访问令牌"""
    url = "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal"
    resp = requests.post(url, json={
        "app_id": APP_ID,
        "app_secret": APP_SECRET
    })
    data = resp.json()
    if data.get("code") != 0:
        raise Exception(f"获取 app_access_token 失败: {data}")
    return data["app_access_token"]


def refresh_access_token(refresh_token: str) -> tuple:
    """
    使用 refresh_token 刷新获取新的 access_token
    返回: (new_access_token, new_refresh_token)
    """
    url = "https://open.feishu.cn/open-apis/authen/v1/refresh_access_token"
    resp = requests.post(url, json={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "app_id": APP_ID,
        "app_secret": APP_SECRET
    })
    data = resp.json()
    if data.get("code") != 0:
        # 将错误信息作为异常抛出，包含错误码和消息
        error_code = data.get("code")
        error_msg = data.get("msg", "")
        error_info = {
            "code": error_code,
            "msg": error_msg,
            "data": data
        }
        raise Exception(f"刷新 access_token 失败: {error_info}")
    d = data.get("data", {})
    return d.get("access_token"), d.get("refresh_token")


def upload_to_bitable(app_token: str, file_data: bytes, file_name: str, access_token: str) -> str:
    """上传文件到多维表格并返回 file_token"""
    url = f"https://open.feishu.cn/open-apis/drive/v1/medias/upload_all"
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    files = {
        "file": (file_name, file_data, "image/png")
    }
    
    data = {
        "file_name": file_name,
        "parent_type": "bitable_file",
        "parent_node": app_token,
        "size": str(len(file_data))
    }
    
    resp = requests.post(url, headers=headers, files=files, data=data)
    result = resp.json()
    
    if result.get("code") != 0:
        error_code = result.get("code")
        error_msg = result.get("msg", "")
        # 检查是否是权限错误 (1061004: forbidden)
        if error_code == 1061004 or "forbidden" in error_msg.lower():
            raise PermissionError(f"上传文件权限不足 (1061004): {result}")
        raise Exception(f"上传文件失败: {result}")
    
    return result["data"]["file_token"]


def create_bitable_record(app_token: str, table_id: str, fields: dict, access_token: str) -> str:
    """在多维表格中创建记录"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    resp = requests.post(url, headers=headers, json={"fields": fields})
    result = resp.json()
    
    if result.get("code") != 0:
        raise Exception(f"创建记录失败: {result}")
    
    return result["data"]["record"]["record_id"]


def update_bitable_record(app_token: str, table_id: str, record_id: str, fields: dict, access_token: str) -> str:
    """更新多维表格中的记录"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    resp = requests.put(url, headers=headers, json={"fields": fields})
    result = resp.json()
    
    if result.get("code") != 0:
        raise Exception(f"更新记录失败: {result}")
    
    return result["data"]["record"]["record_id"]


def get_bitable_records(app_token: str, table_id: str, access_token: str, page_size: int = 500) -> list:
    """获取多维表格中的所有记录"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    all_records = []
    page_token = None
    
    while True:
        params = {"page_size": page_size}
        if page_token:
            params["page_token"] = page_token
        
        resp = requests.get(url, headers=headers, params=params)
        result = resp.json()
        
        if result.get("code") != 0:
            raise Exception(f"获取记录列表失败: {result}")
        
        data = result.get("data", {})
        records = data.get("items", [])
        all_records.extend(records)
        
        # 检查是否还有下一页
        page_token = data.get("page_token")
        if not page_token or not records:
            break
    
    return all_records


def get_bitable_record_by_index(app_token: str, table_id: str, record_index: int, access_token: str) -> Optional[str]:
    """
    根据记录条索引获取对应的记录ID
    record_index: 1表示第一条记录，2表示第二条，以此类推
    返回: 记录ID，如果不存在则返回None
    """
    try:
        records = get_bitable_records(app_token, table_id, access_token)
        
        # record_index 从1开始，所以需要减1作为数组索引
        if record_index > 0 and record_index <= len(records):
            return records[record_index - 1].get("record_id")
        
        return None
    except Exception as e:
        log_to_file(f"[get_bitable_record_by_index] Error: {e}")
        return None


def get_bitable_record_data(app_token: str, table_id: str, record_id: str, access_token: str) -> Optional[dict]:
    """
    根据记录ID获取单条记录的完整数据
    返回: 记录的字段数据字典，如果不存在则返回None
    """
    try:
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}"
        
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        log_to_file(f"[get_bitable_record_data] 请求URL: {url}")
        log_to_file(f"[get_bitable_record_data] 记录ID: {record_id}")
        
        resp = requests.get(url, headers=headers)
        result = resp.json()
        
        log_to_file(f"[get_bitable_record_data] API响应code: {result.get('code')}")
        
        if result.get("code") != 0:
            log_to_file(f"[get_bitable_record_data] API Error: {result}")
            return None
        
        record = result.get("data", {}).get("record")
        if not record:
            log_to_file(f"[get_bitable_record_data] 记录不存在")
            return None
        
        fields = record.get("fields", {})
        log_to_file(f"[get_bitable_record_data] 获取到的字段数量: {len(fields)}")
        log_to_file(f"[get_bitable_record_data] 字段ID列表: {list(fields.keys())}")
        
        # 返回记录的字段数据
        return fields
    except Exception as e:
        log_to_file(f"[get_bitable_record_data] Error: {e}")
        import traceback
        log_to_file(f"[get_bitable_record_data] Traceback: {traceback.format_exc()}")
        return None


def get_table_fields(app_token: str, table_id: str, access_token: str) -> list:
    """获取多维表格字段列表"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    resp = requests.get(url, headers=headers, params={"page_size": 100})
    result = resp.json()
    
    if result.get("code") != 0:
        raise Exception(f"获取字段列表失败: {result}")
    
    return result["data"]["items"]


# ==================== API 路由 ====================

@router.get("/table-fields")
def get_table_fields_api(app_token: str, table_id: str, session_id: Optional[str] = None):
    """获取多维表格的字段列表，供前端创建表单时选择"""
    try:
        access_token = None
        token_data = None
        
        print(f"[table-fields] Getting fields for app_token={app_token}, table_id={table_id}")
        
        # 获取 session 中的 token
        if session_id:
            try:
                from main import USER_TOKENS
                token_data = USER_TOKENS.get(session_id)
                if token_data:
                    access_token = token_data.get("access_token")
                    print(f"[table-fields] Using user access_token from session")
            except Exception as e:
                print(f"[table-fields] Failed to get session token: {e}")
        
        # 尝试获取字段列表
        raw_fields = None
        
        # 第一次尝试：使用已有的 access_token
        if access_token:
            try:
                raw_fields = get_table_fields(app_token, table_id, access_token)
                print(f"[table-fields] Got {len(raw_fields)} fields using user token")
            except Exception as e:
                print(f"[table-fields] User token failed: {e}")
                # token 可能过期，尝试刷新
                if token_data and token_data.get("refresh_token"):
                    try:
                        new_access, new_refresh = refresh_access_token(token_data.get("refresh_token"))
                        access_token = new_access
                        # 更新存储
                        from session_store import update_session
                        update_session(session_id, {
                            "access_token": new_access,
                            "refresh_token": new_refresh
                        })
                        raw_fields = get_table_fields(app_token, table_id, access_token)
                        print(f"[table-fields] Got {len(raw_fields)} fields using refreshed token")
                    except Exception as refresh_e:
                        print(f"[table-fields] Refresh token failed: {refresh_e}")
        
        # 回退到应用 token
        if raw_fields is None:
            print(f"[table-fields] Falling back to app token")
            try:
                access_token = get_app_access_token()
                print(f"[table-fields] Got app_access_token")
                raw_fields = get_table_fields(app_token, table_id, access_token)
                print(f"[table-fields] Got {len(raw_fields)} fields using app token")
            except Exception as app_e:
                print(f"[table-fields] App token also failed: {app_e}")
                raise app_e
        
        # 转换为前端可用格式
        fields = []
        for f in raw_fields:
            field_type = f.get("type", 1)
            
            # 跳过不支持的字段类型
            if field_type in UNSUPPORTED_FIELD_TYPES:
                continue
            
            input_type = FIELD_TYPE_MAP.get(field_type, "text")
            
            # 提取单选/多选选项
            options = []
            if field_type in (3, 4):  # 单选或多选
                property_data = f.get("property", {})
                option_list = property_data.get("options", [])
                options = [opt.get("name", "") for opt in option_list if opt.get("name")]
            
            fields.append({
                "field_id": f.get("field_id", ""),
                "field_name": f.get("field_name", ""),
                "label": f.get("field_name", ""),
                "type": field_type,
                "input_type": input_type,
                "options": options,
                "required": False,
                "placeholder": f"请输入{f.get('field_name', '')}"
            })
        
        return {"success": True, "fields": fields}
    
    except Exception as e:
        print(f"[table-fields] ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取字段列表失败: {str(e)}")


@router.get("/record-count")
def get_record_count_api(app_token: str, table_id: str, session_id: Optional[str] = None):
    """获取多维表格的记录数量"""
    try:
        access_token = None
        token_data = None
        
        print(f"[record-count] Getting record count for app_token={app_token}, table_id={table_id}")
        
        # 获取 session 中的 token
        if session_id:
            try:
                from main import USER_TOKENS
                token_data = USER_TOKENS.get(session_id)
                if token_data:
                    access_token = token_data.get("access_token")
                    print(f"[record-count] Using user access_token from session")
            except Exception as e:
                print(f"[record-count] Failed to get session token: {e}")
        
        # 尝试获取记录列表
        records = None
        
        # 第一次尝试：使用已有的 access_token
        if access_token:
            try:
                records = get_bitable_records(app_token, table_id, access_token)
                print(f"[record-count] Got {len(records)} records using user token")
            except Exception as e:
                print(f"[record-count] User token failed: {e}")
                # token 可能过期，尝试刷新
                if token_data and token_data.get("refresh_token"):
                    try:
                        new_access, new_refresh = refresh_access_token(token_data.get("refresh_token"))
                        access_token = new_access
                        # 更新存储
                        from session_store import update_session
                        update_session(session_id, {
                            "access_token": new_access,
                            "refresh_token": new_refresh
                        })
                        records = get_bitable_records(app_token, table_id, access_token)
                        print(f"[record-count] Got {len(records)} records using refreshed token")
                    except Exception as refresh_e:
                        print(f"[record-count] Refresh token failed: {refresh_e}")
        
        # 回退到应用 token
        if records is None:
            print(f"[record-count] Falling back to app token")
            try:
                access_token = get_app_access_token()
                print(f"[record-count] Got app_access_token")
                records = get_bitable_records(app_token, table_id, access_token)
                print(f"[record-count] Got {len(records)} records using app token")
            except Exception as app_e:
                print(f"[record-count] App token also failed: {app_e}")
                raise app_e
        
        return {"success": True, "count": len(records)}
    
    except Exception as e:
        print(f"[record-count] ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取记录数量失败: {str(e)}")


@router.post("/create")
def create_form(req: CreateFormRequest, db: Session = Depends(get_db)):
    """创建外部签名表单"""
    form_id = generate_form_id()
    
    # 序列化字段配置（优先使用 fields，兼容 extra_fields）
    fields_to_save = req.fields or req.extra_fields or []
    extra_fields_json = None
    if fields_to_save:
        extra_fields_json = json.dumps([f.dict() for f in fields_to_save], ensure_ascii=False)
    
    # 从 main.py 的 USER_TOKENS 获取创建者的 refresh_token
    creator_refresh_token = None
    
    if req.session_id:
        try:
            from main import USER_TOKENS
            token_data = USER_TOKENS.get(req.session_id)
            if token_data:
                creator_refresh_token = token_data.get("refresh_token")
        except Exception as e:
            log_to_file(f"[Form Create] Failed to get refresh_token: {e}")
    
    form = SignForm(
        form_id=form_id,
        name=req.name,
        description=req.description,
        app_token=req.app_token,
        table_id=req.table_id,
        signature_field_id=req.signature_field_id,
        extra_fields=extra_fields_json,
        created_by=req.created_by,
        creator_session_id=req.session_id,  # 保存创建者的 session_id（用于获取最新的 refresh_token）
        creator_refresh_token=creator_refresh_token,  # 保存创建者的 refresh_token（作为备用）
        record_index=req.record_index or 1,  # 保存记录条索引，默认为1
        show_data=req.show_data or False  # 保存是否显示数据的标记
    )
    
    db.add(form)
    db.commit()
    db.refresh(form)
    
    has_auth = creator_refresh_token is not None
    
    if not has_auth:
        log_to_file(f"[Form Create] Form {form_id} created without authorization")
    
    return {
        "success": True,
        "form_id": form_id,
        "share_url": f"/sign/{form_id}",  # 前端路由
        "has_auth": has_auth,  # 告知前端是否保存了授权
        "warning": None if has_auth else "表单已创建，但未保存用户授权信息。如需上传文件，请重新授权后重新创建表单。"
    }


@router.get("/{form_id}/config")
def get_form_config(form_id: str, db: Session = Depends(get_db)):
    """获取表单配置（公开接口，无需认证）"""
    form = db.query(SignForm).filter(
        SignForm.form_id == form_id,
        SignForm.is_active.is_(True)
    ).first()
    
    if not form:
        raise HTTPException(status_code=404, detail="表单不存在或已过期")
    
    # 检查是否过期
    if form.expires_at and form.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="表单已过期")
    
    # 解析字段配置
    fields = []
    if form.extra_fields:
        try:
            fields = json.loads(form.extra_fields)
        except:
            fields = []
    
    # 确定是否需要签名（检查是否有附件类型字段）
    signature_required = bool(form.signature_field_id)
    if not signature_required:
        for f in fields:
            if f.get("input_type") == "attachment" or f.get("type") == 17:
                signature_required = True
                break
    
    return {
        "form_id": form.form_id,
        "name": form.name,
        "description": form.description,
        "fields": fields,
        "signature_field_id": form.signature_field_id,
        "signature_required": signature_required,
        "show_data": form.show_data,  # 返回是否显示数据的标记
        "record_index": form.record_index  # 返回记录条索引
    }


@router.get("/{form_id}/record-data")
def get_form_record_data(form_id: str, db: Session = Depends(get_db)):
    """获取表单关联记录的数据（公开接口，无需认证）"""
    form = db.query(SignForm).filter(
        SignForm.form_id == form_id,
        SignForm.is_active.is_(True)
    ).first()
    
    if not form:
        raise HTTPException(status_code=404, detail="表单不存在或已过期")
    
    # 检查是否过期
    if form.expires_at and form.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="表单已过期")
    
    # 检查是否启用了显示数据功能
    if not form.show_data:
        raise HTTPException(status_code=400, detail="该表单未启用显示数据功能")
    
    # 检查是否有有效的记录索引
    if not form.record_index or form.record_index <= 0:
        raise HTTPException(status_code=400, detail="该表单未关联有效记录")
    
    # 获取 access_token（优先使用创建者的 token，fallback 到 app token）
    access_token = None
    
    # 尝试使用创建者的 refresh_token 获取 access_token
    if form.creator_refresh_token:
        try:
            new_access_token, new_refresh_token = refresh_access_token(form.creator_refresh_token)
            access_token = new_access_token

            
            # 🔧 关键修复：刷新成功后立即更新数据库中的 refresh_token
            if new_refresh_token:
                form.creator_refresh_token = new_refresh_token
                db.commit()

                
                # 同时更新 USER_TOKENS（如果 session_id 存在）
                if form.creator_session_id:
                    try:
                        from session_store import update_session
                        update_session(form.creator_session_id, {
                            "refresh_token": new_refresh_token,
                            "access_token": new_access_token
                        })

                    except Exception as token_update_err:
                        log_to_file(f"[get_form_record_data] ⚠️ Failed to update USER_TOKENS: {token_update_err}")
        except Exception as e:
            log_to_file(f"[get_form_record_data] Failed to refresh creator token: {e}")
    
    # 如果获取失败，使用 app token
    if not access_token:
        try:
            access_token = get_app_access_token()

        except Exception as e:
            log_to_file(f"[get_form_record_data] Failed to get app token: {e}")
            raise HTTPException(status_code=500, detail="无法获取访问令牌")

    
    # 根据 record_index 获取记录ID
    try:
        record_id = get_bitable_record_by_index(
            form.app_token,
            form.table_id,
            form.record_index,
            access_token
        )
        
        if not record_id:
            raise HTTPException(status_code=404, detail=f"记录条{form.record_index}不存在")
        
        # 获取记录的完整数据
        record_fields = get_bitable_record_data(
            form.app_token,
            form.table_id,
            record_id,
            access_token
        )
        

        
        if not record_fields:
            raise HTTPException(status_code=404, detail="无法获取记录数据")
        
        # 解析表单字段配置，用于数据转换
        form_fields = []
        if form.extra_fields:
            try:
                form_fields = json.loads(form.extra_fields)
            except:
                form_fields = []
        
        # 获取字段列表，建立字段名称到字段ID的映射
        # 飞书API返回的记录数据使用字段名称作为键，而不是字段ID
        field_name_to_id_map = {}
        try:
            raw_fields = get_table_fields(form.app_token, form.table_id, access_token)
            for f in raw_fields:
                field_name = f.get("field_name", "")
                field_id = f.get("field_id", "")
                if field_name and field_id:
                    field_name_to_id_map[field_name] = field_id

        except Exception as e:
            log_to_file(f"[get_form_record_data] 获取字段列表失败: {e}")
            # 如果获取失败，尝试直接使用字段名称匹配
        
        # 转换数据格式，只返回表单中配置的字段
        converted_data = {}
        field_id_map = {f.get("field_id"): f for f in form_fields}
        

        
        # 将记录数据中的字段名称转换为字段ID
        for field_key, value in record_fields.items():
            # 尝试将字段键（可能是名称或ID）转换为字段ID
            field_id = None
            
            # 如果字段键已经是字段ID（以fld开头），直接使用
            if field_key.startswith("fld"):
                field_id = field_key
            # 否则，尝试通过字段名称映射查找字段ID
            elif field_key in field_name_to_id_map:
                field_id = field_name_to_id_map[field_key]
            
            if not field_id:
                continue
            
            if field_id not in field_id_map:
                continue
            
            field_config = field_id_map[field_id]
            input_type = field_config.get("input_type", "text")
            

            
            # 根据字段类型转换数据
            if value is None:
                converted_data[field_id] = None
            elif input_type == "number":
                # 数字类型
                try:
                    converted_data[field_id] = float(value) if value else None
                except:
                    converted_data[field_id] = None
            elif input_type == "checkbox":
                # 复选框：布尔值
                converted_data[field_id] = bool(value)
            elif input_type == "multiselect":
                # 多选：数组
                if isinstance(value, list):
                    converted_data[field_id] = [str(item) for item in value]
                else:
                    converted_data[field_id] = [str(value)] if value else []
            elif input_type == "date":
                # 日期：时间戳转日期字符串
                if isinstance(value, (int, float)) and value > 0:
                    # 飞书日期时间戳是毫秒
                    dt = datetime.fromtimestamp(value / 1000)
                    converted_data[field_id] = dt.strftime("%Y-%m-%d")
                else:
                    converted_data[field_id] = None
            elif input_type == "attachment":
                # 附件：返回 file_token 数组（前端仅显示提示）
                if isinstance(value, list) and len(value) > 0:
                    # 提取 file_token
                    file_tokens = []
                    for item in value:
                        if isinstance(item, dict):
                            token = item.get("file_token") or item.get("token")
                            if token:
                                file_tokens.append(token)
                    converted_data[field_id] = file_tokens if file_tokens else None
                else:
                    converted_data[field_id] = None
            else:
                # 文本、电话、邮箱、URL、单选等：直接使用字符串
                converted_data[field_id] = str(value) if value else ""
            

        

        
        return {
            "success": True,
            "data": converted_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log_to_file(f"[get_form_record_data] Error: {e}")
        raise HTTPException(status_code=500, detail=f"获取记录数据失败: {str(e)}")


@router.post("/{form_id}/submit")
async def submit_form(
    form_id: str,
    signature: Optional[UploadFile] = File(None),  # 签名改为可选
    form_data: str = Form(default="{}"),
    db: Session = Depends(get_db)
):
    """提交签名表单（公开接口）"""
    # 查找表单（使用行锁防止并发刷新 token）
    form = db.query(SignForm).filter(
        SignForm.form_id == form_id,
        SignForm.is_active.is_(True)
    ).with_for_update().first()
    
    if not form:
        raise HTTPException(status_code=404, detail="表单不存在")
    
    if form.expires_at and form.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="表单已过期")
    
    try:
        # 优先使用创建者的 refresh_token 刷新获取 access_token
        access_token = None
        token_type = "none"  # 记录使用的 token 类型
        is_20026_fallback = False  # 记录是否是 20026 错误导致的 fallback
        
        # 🔧 修复：始终从数据库获取最新的 refresh_token（因为 get_form_record_data 会更新它）
        current_refresh_token = form.creator_refresh_token
        session_id = form.creator_session_id
        
        log_to_file(f"[Form Submit] Token status: refresh_token={'exists' if current_refresh_token else 'missing'}")
        
        # 使用 refresh_token 刷新获取 access_token
        if current_refresh_token:
            max_retries = 2  # 最多重试2次（初始尝试 + 1次重试）
            retry_count = 0
            refresh_success = False
            
            while retry_count < max_retries and not refresh_success:
                try:
                    new_access_token, new_refresh_token = refresh_access_token(current_refresh_token)
                    access_token = new_access_token
                    token_type = "user_token"
                    log_to_file(f"[Form Submit] Successfully refreshed user token (attempt {retry_count + 1})")
                    refresh_success = True
                    
                    # 立即更新存储的 refresh_token（飞书每次刷新都会返回新的 refresh_token，旧的会失效）
                    if new_refresh_token:
                        # 同时更新数据库和 USER_TOKENS
                        form.creator_refresh_token = new_refresh_token
                        db.commit()
                        log_to_file(f"[Form Submit] Updated refresh_token in database")
                        
                        # 如果 session_id 存在，也更新 USER_TOKENS
                        if session_id:
                            try:
                                from session_store import update_session
                                update_session(session_id, {
                                    "refresh_token": new_refresh_token,
                                    "access_token": new_access_token
                                })
                                log_to_file(f"[Form Submit] Updated refresh_token in USER_TOKENS[session_id]")
                            except Exception as e:
                                log_to_file(f"[Form Submit] ⚠️ Failed to update USER_TOKENS: {e}")
                except Exception as refresh_err:
                    error_msg = str(refresh_err)
                    log_to_file(f"[Form Submit] Refresh failed (attempt {retry_count + 1}): {error_msg}")
                    print(f"[Form Submit] Refresh failed: {refresh_err}")
                    
                    # 检查是否是 refresh_token 已被使用的错误（错误码 20026）
                    # 注意：20026 错误的错误消息包含 "invalid" 和 "used"，所以需要先检查 20026
                    is_token_used = "20026" in error_msg or ("invalid" in error_msg.lower() and "used" in error_msg.lower())
                    log_to_file(f"[Form Submit] Error analysis: is_token_used={is_token_used}, contains_20026={'20026' in error_msg}, contains_invalid={'invalid' in error_msg.lower()}, contains_used={'used' in error_msg.lower()}")
                    log_to_file(f"[Form Submit] retry_count={retry_count}, max_retries={max_retries}")
                    
                    # 如果是 20026 错误，尝试重试或直接 fallback（绝对不能抛出 401）
                    if is_token_used:
                        log_to_file(f"[Form Submit] ✅ Detected 20026 error (token used), will retry or fallback to app_token (NEVER throw 401)")
                        # 如果还有重试机会，从 USER_TOKENS 或数据库获取最新的 refresh_token
                        if retry_count < max_retries - 1:
                            log_to_file(f"[Form Submit] Token was used by another request, getting latest token and retrying...")
                            log_to_file(f"[Form Submit] Current session_id: {session_id}, current_refresh_token (first 20 chars): {current_refresh_token[:20] if current_refresh_token else 'None'}...")
                            try:
                                # 等待一段时间，让另一个请求完成刷新和提交
                                # 第一次等待 0.2 秒，第二次等待 0.5 秒
                                wait_time = 0.2 if retry_count == 0 else 0.5
                                time.sleep(wait_time)
                                
                                # 优先从 USER_TOKENS 获取最新的 refresh_token
                                new_refresh_token = None
                                found_session_id = session_id
                                
                                try:
                                    from main import USER_TOKENS
                                    log_to_file(f"[Form Submit] USER_TOKENS has {len(USER_TOKENS)} sessions: {list(USER_TOKENS.keys())}")
                                    
                                    # 如果有 session_id，先尝试从它获取
                                    if session_id:
                                        token_data = USER_TOKENS.get(session_id)
                                        if token_data and token_data.get("refresh_token"):
                                            test_token = token_data.get("refresh_token")
                                            if test_token != current_refresh_token:
                                                new_refresh_token = test_token
                                                found_session_id = session_id
                                                log_to_file(f"[Form Submit] Got updated refresh_token from USER_TOKENS[session_id={session_id}]")
                                            else:
                                                log_to_file(f"[Form Submit] USER_TOKENS[session_id={session_id}] has same refresh_token, will search other sessions")
                                        else:
                                            log_to_file(f"[Form Submit] USER_TOKENS[session_id={session_id}] not found or no refresh_token, will search other sessions")
                                    
                                    # 如果从 session_id 获取失败，或者没有 session_id，遍历所有 session 查找可用的 refresh_token
                                    if not new_refresh_token:
                                        log_to_file(f"[Form Submit] Searching all USER_TOKENS sessions for available refresh_token...")
                                        # 遍历所有 session，尝试找到可用的 refresh_token
                                        # 优先使用与当前 refresh_token 不同的 token（可能是更新的版本）
                                        for sid in USER_TOKENS.keys():
                                            try:
                                                token_data = USER_TOKENS.get(sid)
                                                if token_data and token_data.get("refresh_token"):
                                                    test_token = token_data.get("refresh_token")
                                                    # 如果找到不同的 refresh_token，使用它（在主循环中会验证有效性）
                                                    if test_token != current_refresh_token:
                                                        new_refresh_token = test_token
                                                        found_session_id = sid
                                                        log_to_file(f"[Form Submit] Found different refresh_token in session {sid}, will try it")
                                                        # 同时更新表单的 creator_session_id，以便下次直接使用
                                                        form.creator_session_id = sid
                                                        db.commit()
                                                        log_to_file(f"[Form Submit] Updated form.creator_session_id to {sid}")
                                                        break
                                            except Exception as e:
                                                log_to_file(f"[Form Submit] Error checking session {sid}: {e}")
                                                continue
                                        
                                        if not new_refresh_token:
                                            log_to_file(f"[Form Submit] ⚠️ No different refresh_token found in any session")
                                except Exception as e:
                                    log_to_file(f"[Form Submit] Failed to get refresh_token from USER_TOKENS: {e}")
                                    import traceback
                                    log_to_file(f"[Form Submit] Traceback: {traceback.format_exc()}")
                                
                                # 如果从 USER_TOKENS 获取失败，重新查询数据库
                                if not new_refresh_token:
                                    db.rollback()  # 回滚当前事务，释放锁
                                    form = db.query(SignForm).filter(
                                        SignForm.form_id == form_id,
                                        SignForm.is_active.is_(True)
                                    ).with_for_update().first()
                                    
                                    if not form:
                                        log_to_file(f"[Form Submit] Form not found after retry, falling back to app_token")
                                        access_token = None
                                        break
                                    
                                    if form.creator_refresh_token and form.creator_refresh_token != current_refresh_token:
                                        new_refresh_token = form.creator_refresh_token
                                        log_to_file(f"[Form Submit] Got updated refresh_token from database")
                                
                                # 如果找到了新的 refresh_token，重试
                                if new_refresh_token and new_refresh_token != current_refresh_token:
                                    log_to_file(f"[Form Submit] Found updated refresh_token, retrying with new token")
                                    current_refresh_token = new_refresh_token
                                    retry_count += 1
                                    continue
                                else:
                                    log_to_file(f"[Form Submit] Refresh_token unchanged after wait (attempt {retry_count + 1})")
                                    # refresh_token 未变化，可能是另一个请求还在处理，或者 refresh_token 确实无效
                                    # 如果还有重试机会，再试一次
                                    if retry_count < max_retries - 2:  # 还有一次重试机会
                                        retry_count += 1
                                        continue
                                    else:
                                        # 所有重试都失败，refresh_token 可能已经被之前的请求使用但数据库未更新
                                        # 或者 refresh_token 确实无效
                                        # 对于 20026 错误（token 被并发使用），如果重试后仍失败，应该 fallback 到 app_token
                                        # 而不是直接抛出 401，因为旧版本就是这样处理的，可以正常工作
                                        log_to_file(f"[Form Submit] Refresh_token unchanged after all retries (20026 error), falling back to app_token")
                                        access_token = None
                                        is_20026_fallback = True
                                        break
                            except Exception as db_err:
                                log_to_file(f"[Form Submit] Error during retry logic (20026 error): {db_err}")
                                # 对于 20026 错误，即使重试逻辑出错，也应该 fallback 到 app_token（与旧版本行为一致）
                                log_to_file(f"[Form Submit] Retry logic failed for 20026 error, falling back to app_token")
                                access_token = None
                                is_20026_fallback = True
                                break
                        else:
                            # 没有重试机会了，直接 fallback 到 app_token
                            log_to_file(f"[Form Submit] 20026 error but no more retries (retry_count={retry_count}, max_retries={max_retries}), falling back to app_token")
                            access_token = None
                            is_20026_fallback = True
                            break
                    
                    # 检查是否是 refresh_token 无效或过期的错误（非 20026 的无效错误）
                    # 注意：20026 错误已经在上面处理了，这里只处理其他无效错误
                    # 如果 is_token_used 为 True，说明已经处理过了，不应该继续执行
                    if is_token_used:
                        # 这不应该发生（20026 错误应该在上面已经 break 了），但如果发生了，fallback 到 app_token
                        log_to_file(f"[Form Submit] ⚠️ is_token_used=True but didn't break, falling back to app_token")
                        access_token = None
                        is_20026_fallback = True
                        break
                    
                    # 只有非 20026 错误才会继续执行到这里
                    log_to_file(f"[Form Submit] Non-20026 error, checking if token is invalid/expired")
                    is_invalid_token = False
                    # 只有当错误不是 20026 时，才认为是无效 token
                    # 20026 错误已经在上面处理了，这里只处理其他无效错误
                    if "invalid" in error_msg.lower() and "20026" not in error_msg:
                        is_invalid_token = True
                        log_to_file(f"[Form Submit] Detected invalid token (non-20026)")
                    elif "expired" in error_msg.lower() or "401" in error_msg:
                        is_invalid_token = True
                        log_to_file(f"[Form Submit] Detected expired token or 401 error")
                    
                    # 如果 refresh_token 无效或过期（非并发使用导致的），提示前端需要重新授权
                    if is_invalid_token:
                        log_to_file(f"[Form Submit] Refresh token invalid/expired, clearing it and requiring re-auth")
                        try:
                            form.creator_refresh_token = None
                            db.commit()
                        except Exception as clear_err:
                            log_to_file(f"[Form Submit] Error clearing refresh_token: {clear_err}")
                        # 直接返回 401，让前端引导用户重新授权
                        raise HTTPException(
                            status_code=401,
                            detail="授权已失效，请返回表单管理后台重新完成飞书授权后再提交。"
                        )
                    
                    # 其他错误（非 20026，非 invalid/expired），refresh_token 可能无效
                    # 如果原本有 refresh_token，说明之前授权过，现在失效了，应该要求重新授权
                    # 只有在完全没有 refresh_token 的情况下，才应该使用 app_token
                    if form.creator_refresh_token:
                        log_to_file(f"[Form Submit] Refresh_token exists but refresh failed (non-20026 error), requiring re-auth")
                        try:
                            form.creator_refresh_token = None
                            db.commit()
                            log_to_file(f"[Form Submit] Cleared invalid refresh_token")
                        except Exception as clear_err:
                            log_to_file(f"[Form Submit] Error clearing refresh_token: {clear_err}")
                        raise HTTPException(
                            status_code=401,
                            detail="授权已失效，请返回表单管理后台重新完成飞书授权后再提交。"
                        )
                    else:
                        # 没有 refresh_token，回退到 app_token（但可能没有文件上传权限）
                        log_to_file(f"[Form Submit] No refresh_token, falling back to app_token")
                        access_token = None
                        break
        
        if not access_token:
            # 检查是否需要上传文件（如果有签名文件）
            if signature and signature.filename:
                # 如果是 20026 错误导致的 fallback，不应该抛出 401，而应该尝试使用 app_token 上传（可能会失败，但这是合理的）
                if is_20026_fallback:
                    log_to_file(f"[Form Submit] File upload required but 20026 error fallback, will try app_token (may fail)")
                else:
                    # 需要上传文件，但只有 app_token（没有文件上传权限），要求重新授权
                    log_to_file(f"[Form Submit] File upload required but only app_token available (no upload permission)")
                    raise HTTPException(
                        status_code=401,
                        detail="上传文件需要用户授权。请返回表单管理后台重新完成飞书 OAuth 授权（需要 drive:app 权限），然后重新创建或编辑该表单。"
                    )
            
            log_to_file(f"[Form Submit] Falling back to app_token (user token unavailable)")
            try:
                access_token = get_app_access_token()
                token_type = "app_token"
                log_to_file(f"[Form Submit] Successfully obtained app_token")
            except Exception as app_token_err:
                error_msg = f"获取 app_token 失败: {str(app_token_err)}"
                log_to_file(f"[Form Submit] {error_msg}")
                raise HTTPException(status_code=500, detail=error_msg)
        
        log_to_file(f"[Form Submit] Using token type: {token_type}")
        
        # 确保 form 对象有效（如果之前 rollback 过，form 可能已失效）
        if not form or form.form_id != form_id:
            log_to_file(f"[Form Submit] Form object invalid after rollback, re-querying...")
            form = db.query(SignForm).filter(
                SignForm.form_id == form_id,
                SignForm.is_active.is_(True)
            ).first()
            if not form:
                raise HTTPException(status_code=404, detail="表单不存在")
        
        # 解析表单数据
        extra_data = json.loads(form_data)
        
        # 解析表单字段配置
        field_configs = []
        if form.extra_fields:
            try:
                field_configs = json.loads(form.extra_fields)
            except:
                pass
        
        # 构建字段ID到配置的映射
        field_map = {f.get("field_id"): f for f in field_configs}
        
        # 构建字段ID到字段名称的映射（飞书API需要字段名称而非ID）
        field_id_to_name = {f.get("field_id"): f.get("field_name") or f.get("label") for f in field_configs}
        
        # 构建记录字段
        fields = {}
        
        # 处理签名字段（如果有上传签名）
        file_token = None
        if signature and signature.filename:
            signature_data = await signature.read()
            if signature_data:
                file_name = f"signature_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                try:
                    file_token = upload_to_bitable(form.app_token, signature_data, file_name, access_token)
                except PermissionError as perm_err:
                    # 如果是 20026 错误导致的 fallback，即使上传失败也应该允许提交（不包含签名）
                    # 因为 20026 错误是并发使用导致的，不是真正的权限问题
                    if is_20026_fallback:
                        log_to_file(f"[Form Submit] Upload failed due to 20026 fallback (app_token has no upload permission), but allowing submission without signature. Error: {perm_err}")
                        # 不抛出错误，继续提交表单（不包含签名）
                        file_token = None
                    else:
                        # 权限错误：返回 403
                        error_detail = f"上传文件权限不足。"
                        if token_type == "app_token":
                            error_detail += " 当前使用的是应用 token，缺少文件上传权限。"
                            error_detail += " 请让表单创建者在后台重新完成飞书 OAuth 授权（需要 drive:app 权限），"
                            error_detail += " 然后重新创建或编辑该表单。"
                        else:
                            error_detail += " 当前用户 token 权限不足。"
                            error_detail += " 请检查授权范围是否包含文件上传（drive:app），"
                            error_detail += " 或尝试重新授权后再提交。"
                        log_to_file(f"[Form Submit] Upload permission error: {error_detail}, error: {perm_err}")
                        raise HTTPException(status_code=403, detail=error_detail)
                except Exception as upload_err:
                    # 其他上传错误：记录日志并抛出
                    error_str = str(upload_err)
                    log_to_file(f"[Form Submit] Upload failed with token_type={token_type}: {error_str}")
                    # 检查是否是授权错误
                    if "401" in error_str or "unauthorized" in error_str.lower():
                        error_detail = "上传文件时授权失败。"
                        if token_type == "app_token":
                            error_detail += " 应用 token 可能已过期或无效。"
                            error_detail += " 请让表单创建者在后台重新完成飞书 OAuth 授权，然后重新创建或编辑该表单。"
                        else:
                            error_detail += " 用户 token 可能已过期或无效。"
                            error_detail += " 请返回表单管理后台重新完成飞书 OAuth 授权后再提交。"
                        raise HTTPException(status_code=401, detail=error_detail)
                    # 其他错误返回 500，但包含详细错误信息
                    raise HTTPException(status_code=500, detail=f"上传文件失败: {error_str}")
                
                # 查找附件类型字段
                attachment_field_id = form.signature_field_id
                if not attachment_field_id:
                    for fc in field_configs:
                        if fc.get("input_type") == "attachment" or fc.get("type") == 17:
                            attachment_field_id = fc.get("field_id")
                            break
                
                if attachment_field_id and file_token:
                    # 使用字段名称而非字段ID
                    field_name = field_id_to_name.get(attachment_field_id) or attachment_field_id
                    fields[field_name] = [{"file_token": file_token}]
        
        # 处理其他字段数据（根据类型转换格式）
        for key, value in extra_data.items():
            if not value and value != 0 and value != False:
                continue  # 跳过空值（但保留 0 和 False）
            
            field_config = field_map.get(key, {})
            field_type = field_config.get("type", 1)
            input_type = field_config.get("input_type", "text")
            
            # 获取字段名称（飞书API需要字段名称）
            field_name = field_id_to_name.get(key) or key
            
            # 根据字段类型转换数据格式
            if input_type == "select" or field_type == 3:
                # 单选：转为字符串
                fields[field_name] = str(value) if value else ""
            elif input_type == "multiselect" or field_type == 4:
                # 多选：确保是列表格式
                if isinstance(value, list):
                    fields[field_name] = value
                else:
                    fields[field_name] = [str(value)] if value else []
            elif input_type == "date" or field_type == 5:
                # 日期：转为时间戳（毫秒）
                if isinstance(value, (int, float)):
                    fields[field_name] = int(value)
                elif isinstance(value, str):
                    try:
                        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                        fields[field_name] = int(dt.timestamp() * 1000)
                    except:
                        fields[field_name] = value
                else:
                    fields[field_name] = value
            elif input_type == "number" or field_type == 2:
                # 数字
                try:
                    fields[field_name] = float(value) if '.' in str(value) else int(value)
                except:
                    fields[field_name] = value
            elif input_type == "checkbox" or field_type == 7:
                # 复选框：布尔值
                fields[field_name] = bool(value)
            else:
                # 文本、电话、邮箱、URL 等直接使用字符串
                fields[field_name] = str(value)
        
        # 根据 record_index 决定是更新还是创建记录
        # record_index=0 表示创建新记录，>0 表示更新对应索引的记录
        record_id = None
        record_index = form.record_index  # 不再默认为1，允许0表示创建新记录
        
        # 如果 record_index > 0，尝试获取对应的记录ID
        if record_index > 0:
            try:
                target_record_id = get_bitable_record_by_index(
                    form.app_token, 
                    form.table_id, 
                    record_index, 
                    access_token
                )
                if target_record_id:
                    record_id = target_record_id
                    log_to_file(f"[Form Submit] Found existing record at index {record_index}: {target_record_id}")
            except Exception as e:
                log_to_file(f"[Form Submit] Failed to get record by index {record_index}: {e}")
                # 如果获取失败，继续创建新记录
        
        # 创建或更新多维表格记录
        try:
            if record_id:
                # 更新现有记录
                log_to_file(f"[Form Submit] Updating record {record_id} at index {record_index} with token_type={token_type}, app_token={form.app_token[:8]}..., table_id={form.table_id[:8]}...")
                record_id = update_bitable_record(form.app_token, form.table_id, record_id, fields, access_token)
                log_to_file(f"[Form Submit] Record updated successfully: {record_id}")
            else:
                # 创建新记录
                log_to_file(f"[Form Submit] Creating new record with token_type={token_type}, app_token={form.app_token[:8]}..., table_id={form.table_id[:8]}...")
                record_id = create_bitable_record(form.app_token, form.table_id, fields, access_token)
                log_to_file(f"[Form Submit] Record created successfully: {record_id}")
        except Exception as e:
            # 检查是否是字段未找到错误 (1254045: FieldNameNotFound)
            error_str = str(e)
            operation = "更新" if record_id else "创建"
            print(f"[Form Submit] {operation} record failed: {error_str}")
            log_to_file(f"[Form Submit] {operation} record failed with token_type={token_type}: {error_str}")
            
            # 检查是否是权限错误 (91403: Forbidden)
            if "91403" in error_str or "Forbidden" in error_str or "permission" in error_str.lower():
                error_detail = f"权限不足 (91403 Forbidden)。"
                if token_type == "app_token":
                    error_detail += " 当前使用的是应用 token，缺少多维表格写入权限。"
                    error_detail += " 请让表单创建者在后台重新完成飞书 OAuth 授权（需要 bitable:app 写入权限），"
                    error_detail += " 然后重新创建或编辑该表单。"
                elif token_type == "user_token":
                    error_detail += " 当前用户 token 权限不足。"
                    error_detail += " 请检查授权范围是否包含多维表格写入（bitable:app），"
                    error_detail += " 或尝试重新授权后再提交。"
                else:
                    error_detail += " 未找到有效的用户 token，且应用 token 权限不足。"
                    error_detail += " 请确保表单创建者已完成 OAuth 授权。"
                
                log_to_file(f"[Form Submit] Permission error: {error_detail}")
                # 使用 403 返回给前端，而不是泛化为 500
                raise HTTPException(status_code=403, detail=error_detail)
            
            # 检查是否是授权相关错误（401, 或明确的 unauthorized 错误）
            # 注意：不检查 "token"，因为很多错误信息都包含这个词
            if "401" in error_str or "unauthorized" in error_str.lower() or ("invalid" in error_str.lower() and ("access_token" in error_str.lower() or "token" in error_str.lower())):
                error_detail = "授权失败或 token 无效。"
                if token_type == "app_token":
                    error_detail += " 应用 token 可能已过期或无效。"
                    error_detail += " 请让表单创建者在后台重新完成飞书 OAuth 授权，然后重新创建或编辑该表单。"
                else:
                    error_detail += " 用户 token 可能已过期或无效。"
                    error_detail += " 请返回表单管理后台重新完成飞书 OAuth 授权后再提交。"
                
                log_to_file(f"[Form Submit] Authorization error: {error_detail}")
                raise HTTPException(status_code=401, detail=error_detail)
            
            if "1254045" in error_str or "FieldNameNotFound" in error_str:
                print(f"[Form Submit] Field not found, attempting auto-repair for form {form_id}")
                try:
                    # 获取最新字段列表
                    log_to_file(f"[Form Submit] Fetching table fields...")
                    table_fields = get_table_fields(form.app_token, form.table_id, access_token)
                    log_to_file(f"[Form Submit] Got {len(table_fields)} fields")
                    
                    # 打印所有字段的简要信息
                    for f in table_fields:
                        log_to_file(f"Field: {f.get('field_name')}, Type: {f.get('type')}, ID: {f.get('field_id')}")
                    
                    # 查找附件字段 (type 17 是附件)
                    new_field_id = None
                    # 注意：飞书 API 文档说附件是 17，但为了保险，我们打印出来确认一下
                    attachment_fields = [f for f in table_fields if f.get("type") == 17]
                    print(f"[Form Submit] Found {len(attachment_fields)} attachment fields: {[f.get('field_name') for f in attachment_fields]}")
                    
                    # 策略1：优先找名字包含 "签名" 或 "Signature" 的
                    for f in attachment_fields:
                        if "签名" in f.get("field_name", "") or "sign" in f.get("field_name", "").lower():
                            new_field_id = f["field_id"]
                            log_to_file(f"[Form Submit] Matched signature field: {f.get('field_name')} ({new_field_id})")
                            break
                    
                    # 策略2：如果没找到明确命名的签名列，使用第一个可用的附件字段
                    if not new_field_id and attachment_fields:
                        # 直接使用第一个附件字段，不管ID是否和原来一样
                        # 因为既然报错了，说明原来的提交有问题，我们用最新获取的字段信息重试一次
                        f = attachment_fields[0]
                        new_field_id = f["field_id"]
                        log_to_file(f"[Form Submit] Using fallback attachment field: {f.get('field_name')} ({new_field_id})")
                    
                    if new_field_id:
                        log_to_file(f"[Form Submit] Final decision - New signature field id: {new_field_id}")
                        
                        # 更新 fields 字典
                        # 更新 fields 字典
                        # 彻底移除旧字段数据
                        sig_data = None
                        
                        # 查找并移除旧的签名数据（注意：fields 的键可能是字段名）
                        # 1. 尝试直接用 ID（虽不太可能，但以防万一）
                        if form.signature_field_id in fields:
                            sig_data = fields.pop(form.signature_field_id)
                        
                        # 2. 如果没找到，尝试在 values 中寻找符合特征的数据（附件格式）
                        if not sig_data:
                            for key, value in list(fields.items()):
                                if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict) and 'file_token' in value[0]:
                                    # 找到了疑似签名的数据
                                    log_to_file(f"[Form Submit] Found signature data under key: {key}")
                                    sig_data = fields.pop(key)
                                    break
                        
                        # 如果没有从旧字段拿到数据（理论上不应该），重新构建
                        if not sig_data:
                            if file_token:
                                sig_data = [{"file_token": file_token}]
                                log_to_file("[Form Submit] Reconstructed signature data from file_token")
                            else:
                                log_to_file("[Form Submit] Warning: No signature data found to migrate")
                        
                        if sig_data:
                            # 确定新字段的键名（ID 或 名称）
                            # 飞书 API 通常需要字段名称，特别是当字段名不是随机ID时
                            field_key = new_field_id
                            
                            # 尝试获取字段名称
                            target_field_name = None
                            for f in attachment_fields:
                                if f["field_id"] == new_field_id:
                                    target_field_name = f.get("field_name")
                                    break
                            
                            if target_field_name:
                                field_key = target_field_name
                                log_to_file(f"[Form Submit] Using field name as key: {field_key}")
                                
                            fields[field_key] = sig_data
                        
                        # 打印一下最终的 fields 键
                        print(f"[Form Submit] Retrying with fields keys: {list(fields.keys())}")
                        
                        # 重试创建或更新记录
                        try:
                            if record_id:
                                record_id = update_bitable_record(form.app_token, form.table_id, record_id, fields, access_token)
                            else:
                                record_id = create_bitable_record(form.app_token, form.table_id, fields, access_token)
                        except Exception as retry_err:
                            log_to_file(f"[Form Submit] Retry failed: {retry_err}")
                            raise retry_err
                        
                        # 如果成功，更新数据库
                        form.signature_field_id = new_field_id
                        db.commit()
                        log_to_file(f"[Form Submit] Auto-repair successful, updated form config")
                    else:
                        print(f"[Form Submit] No suitable new attachment field found (all match old ID or none exist)")
                        raise Exception("自动修复失败：未找到新的有效附件字段，请在多维表格中新建一个名为'签名'的附件列")
                except Exception as repair_err:
                    print(f"[Form Submit] Auto-repair failed: {repair_err}")
                    # 抛出修复失败的详细信息，而不是原始异常
                    raise Exception(f"自动修复失败: {str(repair_err)}")
            else:
                raise e  # 其他错误，直接抛出
        
        # 更新提交计数
        form.submit_count += 1
        db.commit()
        
        return {
            "success": True,
            "record_id": record_id,
            "message": "签名提交成功"
        }
        
    except HTTPException:
        # 已经是带状态码的业务错误，直接抛出
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        log_to_file(f"[Form Submit] Unexpected error: {str(e)}\n{error_trace}")
        print(f"[Form Submit] Unexpected error: {str(e)}\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"提交失败: {str(e)}")


@router.get("/list")
def list_forms(created_by: Optional[str] = None, db: Session = Depends(get_db)):
    """获取表单列表"""
    query = db.query(SignForm).filter(SignForm.is_active.is_(True))
    
    if created_by:
        query = query.filter(SignForm.created_by == created_by)
    
    forms = query.order_by(SignForm.created_at.desc()).all()
    
    return {
        "forms": [{
            "form_id": f.form_id,
            "name": f.name,
            "submit_count": f.submit_count,
            "created_at": int(f.created_at.timestamp())
        } for f in forms]
    }


@router.delete("/{form_id}")
def delete_form(form_id: str, db: Session = Depends(get_db)):
    """删除表单（软删除）"""
    form = db.query(SignForm).filter(SignForm.form_id == form_id).first()
    
    if not form:
        raise HTTPException(status_code=404, detail="表单不存在")
    
    form.is_active = False
    db.commit()
    
    return {"success": True}
