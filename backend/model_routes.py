"""Explicit two-step model intent planning; fixed-rule execution after confirmation."""
from fastapi import HTTPException
from pydantic import BaseModel,Field
import app as core
class PlanInput(BaseModel):
    question:str=Field(min_length=1,max_length=2000)
    allow_question_transmission:bool=False
class ConfirmInput(BaseModel):
    plan_id:str
    confirmed_query:dict

def install(app):
    @app.post('/api/v1/analysis/plan',status_code=201)
    def plan(body:PlanInput):
        if not body.allow_question_transmission:raise HTTPException(422,'请明确确认允许将此问题发送至管理员配置的模型供应商；不会发送财务指标行')
        from agents.provider import Provider
        try:
            intent=Provider(transport=getattr(app.state,'model_test_transport',None)).plan(body.question)
        except (RuntimeError,ValueError) as ex:
            if str(ex)=='unsupported_model_request':raise HTTPException(422,'unsupported_model_request：仅支持授权的只读财务指标查询，请明确期间与币种') from None
            code=str(ex) if str(ex) in ('model_not_configured','model_network_disabled','model_provider_failed') else 'model_intent_invalid'
            raise HTTPException(503,code) from None
        value=core.save_task({'task_id':core.uid(),'type':'model_plan','status':'awaiting_confirmation','question':body.question,'intent':intent.model_dump(),'created_at':core.now()})
        return value
    @app.post('/api/v1/analysis/confirm')
    def confirm(body:ConfirmInput):
        value=core.get_task(body.plan_id)
        if value.get('type')!='model_plan':raise HTTPException(404,'查询计划不存在')
        from agents.runtime import Query
        query=Query(**body.confirmed_query).model_dump()
        if query!=value['intent']['query']:raise HTTPException(409,'确认的期间或币种与计划不同，请重新规划')
        from integrations import execute_analysis
        result=execute_analysis(dict(query,question=value['question'],mode='demo'))
        result.update(mode='model_assisted_confirmed',plan_id=body.plan_id)
        # Persist the label together with the task, rather than only changing HTTP output.
        import json
        with core.current_db().begin() as c:c.execute(core.tasks.update().where(core.tasks.c.id==result['task_id']).values(payload=json.dumps(result,ensure_ascii=False)))
        return result
