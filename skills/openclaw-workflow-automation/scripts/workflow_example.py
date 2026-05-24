#!/usr/bin/env python3
"""
OpenClaw Workflow Automation - 工作流示例
演示如何创建一个简单的客服自动回复工作流
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

class WorkflowEngine:
    """简单的工作流引擎"""
    
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.history = []
    
    def _load_config(self, path: str) -> Dict:
        """加载工作流配置"""
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
        return {"triggers": [], "actions": []}
    
    def add_trigger(self, trigger_type: str, condition: Dict):
        """添加触发器"""
        self.config["triggers"].append({
            "type": trigger_type,
            "condition": condition
        })
    
    def add_action(self, action_type: str, params: Dict):
        """添加动作"""
        self.config["actions"].append({
            "type": action_type,
            "params": params
        })
    
    def execute(self, input_data: Dict) -> Dict:
        """执行工作流"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "input": input_data,
            "actions_executed": []
        }
        
        # 检查触发条件
        for trigger in self.config["triggers"]:
            if self._check_trigger(trigger, input_data):
                # 执行动作
                for action in self.config["actions"]:
                    action_result = self._execute_action(action, input_data)
                    result["actions_executed"].append(action_result)
        
        self.history.append(result)
        return result
    
    def _check_trigger(self, trigger: Dict, input_data: Dict) -> bool:
        """检查触发条件"""
        # 简化实现，实际可根据 trigger type 实现复杂逻辑
        if trigger["type"] == "keyword":
            keywords = trigger["condition"].get("keywords", [])
            message = input_data.get("message", "").lower()
            return any(kw.lower() in message for kw in keywords)
        elif trigger["type"] == "time":
            # 时间触发器
            return True
        return False
    
    def _execute_action(self, action: Dict, input_data: Dict) -> Dict:
        """执行动作"""
        return {
            "type": action["type"],
            "params": action["params"],
            "status": "executed",
            "timestamp": datetime.now().isoformat()
        }


# 示例工作流配置
def create_customer_service_workflow():
    """创建客服自动回复工作流"""
    workflow = WorkflowEngine("/tmp/workflow_config.json")
    
    # 添加关键词触发器
    workflow.add_trigger("keyword", {
        "keywords": ["价格", "多少钱", "收费", "费用"]
    })
    
    # 添加回复动作
    workflow.add_action("reply", {
        "message": "您好！我们的 OpenClaw 安装服务价格如下：\n\n"
                   "• 基础安装：¥99\n"
                   "• 高级配置：¥299\n"
                   "• 企业定制：¥999\n\n"
                   "请回复您的需求，我们会尽快为您安排！"
    })
    
    return workflow


if __name__ == "__main__":
    # 示例：创建并测试工作流
    workflow = create_customer_service_workflow()
    
    # 模拟用户输入
    test_input = {
        "user": "customer_001",
        "message": "请问安装服务多少钱？"
    }
    
    # 执行工作流
    result = workflow.execute(test_input)
    print(json.dumps(result, indent=2, ensure_ascii=False))
