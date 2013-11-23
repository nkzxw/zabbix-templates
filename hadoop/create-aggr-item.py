#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import pyzabbix
import re

def main(args):

    zapi = pyzabbix.ZabbixAPI('http://%s' % args.zabbix_server)
    zapi.login(args.zabbix_username, args.zabbix_password)

    for host in args.host:
        process(zapi, host)

def process(zapi, host):

    host = zapi.host.get(filter={'host': host})
    hostid = host[0]['hostid']

    application = zapi.application.get(hostids=hostid, filter={'name': 'iostat'})
    applicationid = application[0]['applicationid']

    items = zapi.item.get(hostids=hostid,
                          search={'key_': 'iostat'},
                          startSearch=True,
                          output=['key_', 'params'])
    devices = {}
    ptrn_device = re.compile(r'iostat\[([^,]+),\s*([^\]]+)\]')
    for item in items:
        mo = ptrn_device.match(item['key_'])
        if mo is None:
            continue
        device_name = mo.group(1)
        if device_name not in devices:
            devices[device_name] = {}
        device_info = devices[device_name]
        device_info[mo.group(2)] = (item['itemid'], item['key_'], item['params'])

    metrics = {
        'rkB/s' : (3, 'B'),
        'wkB/s' : (3, 'B'),
        '%util' : (0, '')
    }
    for metric, metric_info in metrics.iteritems():
        print metric
        keys = [v[metric][1] for k, v in devices.iteritems() if k != 'all']
        params = '(%s)/%d' % ('+'.join('last("%s")' % key for key in keys), len(keys))

        if 'all' not in devices:
            devices['all'] = {}

        if metric not in devices['all']:
            print 'create', metric, params

            zapi.item.create(hostid=hostid,
                             name='All Disk %s' % metric,
                             key_='iostat[all,%s]' % metric,
                             type=15,
                             value_type=metric_info[0],
                             params=params,
                             units=metric_info[1],
                             delay=60,
                             applications=[applicationid])

        elif devices['all'][metric][2] != params:
            print 'update', metric, params
            zapi.item.update(itemid=devices['all'][metric][0],
                             params=params)

        else:
            print 'skip', metric

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-z', '--zabbix-server', required=True, help='e.g. zabbix.domain.com:8080')
    parser.add_argument('-u', '--zabbix-username', required=True)
    parser.add_argument('-p', '--zabbix-password', required=True)
    parser.add_argument('-s', '--host', action='append', required=True)
    main(parser.parse_args())