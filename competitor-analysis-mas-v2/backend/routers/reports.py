# -*- coding: utf-8 -*-
"""
backend/routers/reports.py — 报告 REST 端点
"""

import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

# 报告存放目录
_REPORT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "output",
)


@router.get("/api/reports")
async def list_reports():
    """扫描 output/ 目录，列出所有 HTML 报告"""
    results = []
    if os.path.isdir(_REPORT_DIR):
        for fname in os.listdir(_REPORT_DIR):
            if fname.endswith("_analysis_report.html"):
                results.append({
                    "product_name": fname.replace("_analysis_report.html", ""),
                    "file": fname,
                })
    return {"reports": results}


@router.get("/api/reports/{product_name}")
async def get_report(product_name: str):
    """返回指定的 HTML 报告文件"""
    html_path = os.path.join(_REPORT_DIR, f"{product_name}_analysis_report.html")
    if not os.path.isfile(html_path):
        raise HTTPException(status_code=404, detail="报告不存在")
    return FileResponse(html_path, media_type="text/html; charset=utf-8")
