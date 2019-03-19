from distutils.core import setup

setup(
    name='DeviceHiveClient',
    version='1.0',
    packages=['devicehive', 'devicehive.handlers', 'devicehive.transports', 'devicehive.data_formats'],
    url='nclab.csu.edu.cn',
    license='CSU',
    author='Jiang Xin',
    author_email='xinjiang@csu.edu.cn',
    description='This is an implement of devicehive client usecase',
    install_requires=[
         'redis>=2.10.5',
    ],
    entry_points={
        'console_scripts':[
            'devicehive_client=DeviceHiveClient:main.py',
        ]
    }

)
