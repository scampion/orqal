from pymongo import MongoClient
from sklearn import mixture
from datasketch import MinHash, MinHashLSH

def ngrams(sentence, N):
    for i in range(len(sentence) - N + 1):
         yield sentence[i:i + N]


client = MongoClient('mongodb://madlab.irisa.fr:27017/')


def logs(batch_name=None):
    batch = client.orqal.batch.find_one({'_id': batch_name})
    try:
        if batch:
            for j in batch['jobs']:
                job = client.orqal.jobs.find_one({'_id': j, 'current_status': 'exited'})
                yield '\n'.join(job['stderr']), job['inspect']['State']['ExitCode']

        else:
            for job in client.orqal.jobs.find({'current_status' : 'exited'}):
                yield '\n'.join(job['stderr']), job['inspect']['State']['ExitCode']
    except TypeError as e:
        print(str(e))


if __name__ == '__main__':
    minhashes = {}
    lsh = MinHashLSH(threshold=0.5, num_perm=128)
    for i, (m, c) in enumerate(logs()):
        print(i)
        if m not in minhashes.keys():
            h.update(m.encode('utf8'))
            mh = MinHash(num_perm=128)
            for d in ngrams(m, 5):
                mh.update("".join(d).encode('utf-8'))
            minhashes[m] = mh
            print(mh.hashvalues)
            lsh.insert(m, mh)
        if i > 11000:
            break
    X = [v.hashvalues for v in minhashes.values()]
    n_components = range(1, 6)
    models = [mixture.GaussianMixture(n, covariance_type='full').fit(X) for n in n_components]
    bics = [m.bic(np.array(X)) for m in models]
    gmm = models[bics.index(min(bics))]
    gmm.predict(X)

