#!/usr/bin/env python3
"""
_test_verify.py — API 功能验证脚本。
测试所有核心 API 方法，输出 JSON 结果。
"""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from learn_api import LearnAPI
from _config import get_semester


def test(api):
    results = {}

    # 1. get_courses
    courses = api.get_courses()
    results["get_courses"] = {"count": len(courses), "names": [c.get("kcm") for c in courses]}
    if not courses:
        print(json.dumps({"error": "get_courses failed"}, ensure_ascii=False))
        return results

    first = courses[0]
    wlkcid = first["wlkcid"]
    results["first_course"] = {"name": first.get("kcm"), "wlkcid": wlkcid}

    # 2. get_announcements
    try:
        gg = api.get_announcements(wlkcid)
        results["get_announcements"] = {"count": len(gg), "sample": [{"title": x.get("bt",""), "unread": x.get("sfyd")=="否"} for x in gg[:3]]}
    except Exception as e:
        results["get_announcements"] = {"error": str(e)}

    # 3. get_files
    try:
        files = api.get_files(wlkcid)
        results["get_files"] = {"count": len(files), "sample": [{"name": f.get("bt",""), "is_new": f.get("isNew")} for f in files[:3]]}
    except Exception as e:
        results["get_files"] = {"error": str(e)}

    # 4. get_homeworks
    try:
        hws = api.get_homeworks(wlkcid)
        results["get_homeworks"] = {"count": len(hws), "sample": [{"title": h.get("bt",""), "status": h.get("zt","")} for h in hws[:3]]}
    except Exception as e:
        results["get_homeworks"] = {"error": str(e)}

    # 5. get_discussions
    try:
        tl = api.get_discussions(wlkcid)
        results["get_discussions"] = {"count": len(tl)}
    except Exception as e:
        results["get_discussions"] = {"error": str(e)}

    # 6. get_course_detail
    try:
        detail = api.get_course_detail(wlkcid)
        results["get_course_detail"] = {k: len(v) for k, v in detail.items()}
    except Exception as e:
        results["get_course_detail"] = {"error": str(e)}

    # 7. get_questionnaires
    try:
        wj = api.get_questionnaires(wlkcid)
        results["get_questionnaires"] = {"count": len(wj)}
    except Exception as e:
        results["get_questionnaires"] = {"error": str(e)}

    # 8. mark_file_read (test with first unread file if any)
    try:
        files = api.get_files(wlkcid)
        unread = [f for f in files if str(f.get("isNew", "")) == "1"]
        if unread:
            ok = api.mark_file_read(unread[0]["wjid"])
            results["mark_file_read"] = {"tested": True, "success": ok, "file": unread[0].get("bt","")}
        else:
            results["mark_file_read"] = {"tested": False, "reason": "no unread files"}
    except Exception as e:
        results["mark_file_read"] = {"error": str(e)}

    # 9. homework_full_detail
    try:
        hws = api.get_homeworks(wlkcid)
        if hws:
            h = hws[0]
            detail = api.get_homework_full_detail(wlkcid, h.get("zyid",""), h.get("xszyid",""))
            results["homework_full_detail"] = {k: v for k, v in detail.items() if k not in ("attachments",)}
    except Exception as e:
        results["homework_full_detail"] = {"error": str(e)}

    # 10. mark_all_announcements_read (just test the call, not destructive)
    try:
        marked, total = api.mark_all_announcements_read(wlkcid)
        results["mark_all_announcements_read"] = {"marked": marked, "total": total}
    except Exception as e:
        results["mark_all_announcements_read"] = {"error": str(e)}

    return results


if __name__ == "__main__":
    api = LearnAPI()
    if not api.reload_session():
        print(json.dumps({"error": "Session 无效，请先运行 login_manager.py"}, ensure_ascii=False))
        sys.exit(1)

    print(f"学期: {get_semester()}")
    result = test(api)
    print(json.dumps(result, ensure_ascii=False, indent=2))
