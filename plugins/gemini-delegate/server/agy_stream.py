"""Incremental official AGY NDJSON; expose metadata, never intermediate text."""
import json
import re
import time
from accounting import numeric_usage


def _json(line):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('Duplicate event key')
            result[key]=value
        return result
    def constant(value):raise ValueError('Non-finite event number')
    return json.loads(line,object_pairs_hook=pairs,parse_constant=constant)


class AgyStream:
    def __init__(self, on_progress=None):
        self.buffer=bytearray();self.result=None;self.legacy=False
        self.on_progress=on_progress or (lambda:None)
        self.started=time.monotonic();self.events=0;self.steps=set();self.step_usage={};self.file_reads=set()
        self.state={'phase':'startup','processing_started':False,'event_count':0,'step_count':0,'file_read_steps':0}

    def feed(self, data):
        self.buffer.extend(data)
        if len(self.buffer)>2*1024*1024:raise ValueError('Stream line exceeded limit')
        while b'\n' in self.buffer:
            line,_,remaining=self.buffer.partition(b'\n');self.buffer=bytearray(remaining)
            if line.strip():self._event(_json(line.decode('utf-8')))

    def finish(self):
        if self.buffer.strip():self._event(_json(bytes(self.buffer).decode('utf-8')))
        self.buffer.clear()
        return self.result

    def _event(self, event):
        if not isinstance(event,dict):raise ValueError('Invalid stream event')
        if self.result is not None:raise ValueError('Data after terminal result')
        kind=event.get('event')
        # Some official startup failures use the older single JSON envelope.
        # Accept one complete legacy envelope without inventing stream progress.
        if kind is None and event.get('status') in ('SUCCESS','ERROR') and self.events==0:
            self.result=event;self.legacy=True
            return
        if not isinstance(kind,str):raise ValueError('Missing stream event type')
        self.events+=1;self.state['event_count']=self.events
        self.state['last_event_at']=time.time()
        cid=event.get('conversation_id')
        if kind=='init':
            self.state.setdefault('first_init_seconds',round(time.monotonic()-self.started,3))
        elif kind=='step_update':
            step=event.get('step_update')
            if not isinstance(step,dict):raise ValueError('Invalid step update')
            cid=step.get('conversation_id') or cid
            index=step.get('step_index');typ=step.get('step_type');status=step.get('state')
            if isinstance(index,int) and not isinstance(index,bool) and 0<=index<1000000:
                if len(self.steps)>=4096 and index not in self.steps:raise ValueError('Too many steps')
                self.steps.add(index)
                self.state['step_count']=len(self.steps)
                self.state['last_step_index']=index
            for name,value in [('last_step_type',typ),('last_step_state',status),('last_tool',step.get('tool_name'))]:
                if isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9_.:-]{1,80}',value):self.state[name]=value
            if typ in ('view_file','read_file') or step.get('tool_name') in ('view_file','read_file'):
                self.file_reads.add(index if isinstance(index,int) else ('event',self.events))
                self.state['file_read_steps']=len(self.file_reads)
            # A conversation ID or user-input echo alone is not model progress.
            values=numeric_usage(step.get('usage'))
            if typ=='user_input' and not self.state['processing_started']:
                self.state['phase']='awaiting_model'
            active=typ not in (None,'user_input','init') or any(v>0 for v in values.values())
            if active:
                self.state.update(phase='processing',processing_started=True)
                self.state.setdefault('first_progress_seconds',round(time.monotonic()-self.started,3))
            if status=='DONE' and isinstance(index,int) and values:
                previous=self.step_usage.setdefault(index,{})
                for key,value in values.items():previous[key]=max(value,previous.get(key,0))
        elif kind=='result':
            result=event.get('result')
            if not isinstance(result,dict):raise ValueError('Invalid terminal result')
            self.result=result
            cid=result.get('conversation_id') or cid
            if result.get('response') or result.get('structured_output') or any(v>0 for v in numeric_usage(result.get('usage')).values()):
                self.state.update(phase='processing',processing_started=True)
            self.state['terminal_result_received']=True
        if isinstance(cid,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,160}',cid):self.state['conversation_id']=cid
        self.on_progress()

    def snapshot(self):
        return dict(self.state)

    def partial_usage(self):
        usage={}
        for values in self.step_usage.values():
            for key,value in values.items():usage[key]=usage.get(key,0)+value
        return usage
