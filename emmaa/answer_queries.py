import logging
import pickle
from indra.statements.statements import get_statement_by_name
from indra.statements.agent import Agent
from indra.databases.hgnc_client import get_hgnc_id
from indra.explanation.model_checker import ModelChecker
from indra.databases.chebi_client import get_chebi_id_from_name
from indra.databases.mesh_client import get_mesh_id_name
from indra.preassembler.grounding_mapper import gm
from emmaa.model_tests import (StatementCheckingTest, ScopeTestConnector,
                               ModelManager)
from emmaa.model import EmmaaModel
from emmaa.util import get_s3_client


logger = logging.getLogger(__name__)


def get_statement_by_query(query_dict):
    """Get an INDRA Statement object given a query dictionary"""
    stmt_type = query_dict['query']['typeSelection']
    stmt_class = get_statement_by_name(stmt_type)
    subj = get_agent_from_name(query_dict['query']['subjectSelection'])
    obj = get_agent_from_name(query_dict['query']['objectSelection'])
    stmt = stmt_class(subj, obj)
    return stmt


def get_model_list(query_dict):
    return query_dict['query']['models']


def answer_immediate_query(query_dict):
    stmt = get_statement_by_query(query_dict)
    model_names = get_model_list(query_dict)
    results = {}
    for model_name in model_names:
        mm = load_model_manager_from_s3(model_name)
        response = mm.answer_query(stmt)
        results[model_name] = response
    return results


def load_model_manager_from_s3(model_name):
    client = get_s3_client()
    key = f'models/{model_name}/latest_model_manager.pkl'
    logger.info(f'Loading latest model manager for {model_name} model.')
    obj = client.get_object(Bucket='emmaa', Key=key)
    model_manager = pickle.loads(obj['Body'].read())
    return model_manager


def get_agent_from_name(ag_name):
    ag = Agent(ag_name)
    grounding = get_grounding_from_name(ag_name)
    ag.db_refs = {grounding[0]: grounding[1]}
    return ag


def get_grounding_from_name(name):
    # See if it's a gene name
    hgnc_id = get_hgnc_id(name)
    if hgnc_id:
        return ('HGNC', hgnc_id)

    # Check if it's in the grounding map
    try:
        refs = gm[name]
        if isinstance(refs, dict):
            for dbn, dbi in refs.items():
                if dbn != 'TEXT':
                    return (dbn, dbi)
    # If not, search by text
    except KeyError:
        pass

    chebi_id = get_chebi_id_from_name(name)
    if chebi_id:
        return ('CHEBI', f'CHEBI: {chebi_id}')

    mesh_id, _ = get_mesh_id_name(name)
    if mesh_id:
        return ('MESH', mesh_id)