from scripts.audit_agent_data import duplicate_documents, split_collisions, summarize_records


def test_duplicate_documents_preserve_different_numbers_and_fire_driving():
    rows = [{'id':'a','text':'VF8  công suất 150 kW.'}, {'id':'b','text':'VF8 công suất 150 kW.'},
            {'id':'c','text':'VF8 công suất 100 kW.'}, {'id':'d','text':'Xe đang cháy'}, {'id':'e','text':'Xe đang chạy'}]
    result = duplicate_documents(rows)
    assert result == [{'ids':['a','b'], 'excess':1}]


def test_train_test_overlap_and_conflicting_labels_are_reported():
    datasets = {'train':[{'id':'a','input':'Xe không sạc được', 'expected_priority':'HIGH'}],
                'test':[{'id':'b','input':'Xe không sạc được?', 'expected_priority':'MEDIUM'}]}
    result = split_collisions(datasets)
    assert result[0]['datasets'] == ['test','train']
    assert result[0]['conflicting_fields'] == ['expected_priority']


def test_registry_enrichment_is_not_confused_with_absent_raw_metadata():
    rows = [{'id':'a','text':'VF8 thông số', 'source_id':'s', 'applicable_models':'VF8'}]
    result = summarize_records(rows, {'s':{'source_type':'official_catalog'}})
    assert result['raw_missing_source_type'] == 1
    assert result['effective_source_types'] == {'official_catalog':1}
    assert result['unregistered_sources'] == []


def test_nested_golden_labels_are_compared_without_erasing_conversation_context():
    datasets = {'train':[{'id':'a','input':'Xe không sạc được','expected_priority':'HIGH'}],
                'golden':[{'id':'b','turns':[
                    {'input':'Xe không sạc được','expected':{'priority':'MEDIUM'}},
                    {'input':'Xe không sạc được','expected':{'priority':'CRITICAL'}}]}]}
    result = split_collisions(datasets)
    assert len(result) == 1
    assert result[0]['conflicting_fields'] == ['expected_priority']
