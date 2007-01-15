/*
 * svn-archive.c
 * ----------
 *  Walk through a given revision of a local Subversion repository and export 
 *  all of the contents as a tarfile.
 *
 * Author: Chris Lee <clee@kde.org>
 * License: MIT <http://www.opensource.org/licenses/mit-license.php>
 */

#define _XOPEN_SOURCE
#include <unistd.h>
#include <string.h>
#include <stdio.h>
#include <time.h>

#ifndef PATH_MAX
#define PATH_MAX 4096
#endif

#include <apr_general.h>
#include <apr_lib.h>
#include <apr_getopt.h>

#include <svn_types.h>
#include <svn_pools.h>
#include <svn_repos.h>

#undef SVN_ERR
#define SVN_ERR(expr) SVN_INT_ERR(expr)
#define apr_sane_push(arr, contents) *(char **)apr_array_push(arr) = contents

#define TRUNK "/trunk"

static time_t archive_time;

time_t get_epoch(char *svn_date)
{
    struct tm tm = {0};
    char *date = malloc(strlen(svn_date) * sizeof(char *));
    strncpy(date, svn_date, strlen(svn_date) - 8);
    strptime(date, "%Y-%m-%dT%H:%M:%S", &tm);
    free(date);
    return mktime(&tm);
}

int tar_header(apr_pool_t *pool, char *path, char *node, size_t f_size)
{
    char          buf[512];
    unsigned int  i, checksum;
    svn_boolean_t is_dir;

    memset(buf, 0, sizeof(buf));

    fprintf(stderr, "Writing header for path (%s) node (%s)\n", path, node);

    if ((strlen(path) == 0) && (strlen(node) == 0)) {
        return 0;
    }

    if (strlen(node) == 0) {
        is_dir = 1;
    } else {
        is_dir = 0;
    }

    if (strlen(path) == 0) {
        strncpy(buf, apr_psprintf(pool, "%s", node), 99);
    } else if (strlen(path) + strlen(node) < 100) {
        strncpy(buf, apr_psprintf(pool, "%s/%s", path+1, node), 99);
    } else {
        fprintf(stderr, "really long file path...\n");
        strncpy(&buf[0], node, 99);
        strncpy(&buf[345], path+1, 154);
    }

    strncpy(&buf[100], apr_psprintf(pool, "%07o", (is_dir ? 0755 : 0644)), 7);
    strncpy(&buf[108], apr_psprintf(pool, "%07o", 1000), 7);
    strncpy(&buf[116], apr_psprintf(pool, "%07o", 1000), 7);
    strncpy(&buf[124], apr_psprintf(pool, "%011lo", f_size), 11);
    strncpy(&buf[136], apr_psprintf(pool, "%011lo", archive_time), 11);
    strncpy(&buf[156], (is_dir ? "5" : "0"), 1);
    strncpy(&buf[257], "ustar  ", 8);
    strncpy(&buf[265], "clee", 31);
    strncpy(&buf[297], "clee", 31);
    // strncpy(&buf[329], apr_psprintf(pool, "%07o", 0), 7);
    // strncpy(&buf[337], apr_psprintf(pool, "%07o", 0), 7);

    strncpy(&buf[148], "        ", 8);
    checksum = 0;
    for (i = 0; i < sizeof(buf); i++) {
        checksum += buf[i];
    }
    strncpy(&buf[148], apr_psprintf(pool, "%07o", checksum & 0x1fffff), 7);

    fwrite(buf, sizeof(char), sizeof(buf), stdout);

    return 0;
}

int tar_footer()
{
    char block[1024];
    memset(block, 0, sizeof(block));
    fwrite(block, sizeof(char), sizeof(block), stdout);
}

int dump_blob(svn_fs_root_t *root, char *prefix, char *path, char *node, apr_pool_t *pool)
{
    char           *full_path, buf[512];
    apr_size_t     len;
    svn_stream_t   *stream;
    svn_filesize_t stream_length;

    full_path = apr_psprintf(pool, "%s%s/%s", prefix, path, node);

    SVN_ERR(svn_fs_file_length(&stream_length, root, full_path, pool));
    SVN_ERR(svn_fs_file_contents(&stream, root, full_path, pool));

    tar_header(pool, path, node, stream_length);

    do {
        len = sizeof(buf);
        memset(buf, '\0', sizeof(buf));
        SVN_ERR(svn_stream_read(stream, buf, &len));
        fwrite(buf, sizeof(char), sizeof(buf), stdout);
    } while (len == sizeof(buf));

    return 0;
}

int dump_tree(svn_fs_root_t *root, char *prefix, char *path, apr_pool_t *pool)
{
    const void       *key;
    void             *val;
    char             *node, *subpath, *full_path;

    apr_pool_t       *subpool;
    apr_hash_t       *dir_entries;
    apr_hash_index_t *i;

    svn_boolean_t    is_dir;

    tar_header(pool, path, "", 0);

    SVN_ERR(svn_fs_dir_entries(&dir_entries, root, apr_psprintf(pool, "%s/%s", prefix, path), pool));

    subpool = svn_pool_create(pool);

    for (i = apr_hash_first(pool, dir_entries); i; i = apr_hash_next(i)) {
        svn_pool_clear(subpool);
        apr_hash_this(i, &key, NULL, &val);
        node = (char *)key;

        subpath = apr_psprintf(subpool, "%s/%s", path, node);
        full_path = apr_psprintf(subpool, "%s%s", prefix, subpath);

        fprintf(stderr, "in dump_tree, full_path %s\n", full_path);
        svn_fs_is_dir(&is_dir, root, full_path, subpool);

        if (is_dir) {
            dump_tree(root, prefix, subpath, subpool);
        } else {
            dump_blob(root, prefix, path, node, subpool);
        }
    }

    svn_pool_destroy(subpool);

    return 0;
}

int crawl_revisions(char *repos_path, char *root_path)
{
    const void           *key;
    void                 *val;
    char                 *path, *file_change;
 
    apr_pool_t           *pool;
    apr_hash_index_t     *i;
    apr_hash_t           *props;

    svn_fs_t             *fs;
    svn_repos_t          *repos;
    svn_string_t         *author, *committer, *svndate, *svnlog;
    svn_revnum_t         youngest_rev, export_rev;
    svn_boolean_t        is_dir;
    svn_fs_root_t        *root_obj;
    svn_fs_path_change_t *change;

    pool = svn_pool_create(NULL);

    SVN_ERR(svn_repos_open(&repos, repos_path, pool));

    fs = svn_repos_fs(repos);

    SVN_ERR(svn_fs_initialize(pool));
    SVN_ERR(svn_fs_youngest_rev(&youngest_rev, fs, pool));

    export_rev = youngest_rev;

    fprintf(stderr, "Exporting archive of r%ld... \n", export_rev);

    SVN_ERR(svn_fs_revision_root(&root_obj, fs, export_rev, pool));
    SVN_ERR(svn_fs_revision_proplist(&props, fs, export_rev, pool));

    svndate = apr_hash_get(props, "svn:date", APR_HASH_KEY_STRING);
    archive_time = get_epoch((char *)svndate->data);

    dump_tree(root_obj, root_path, "", pool);

    tar_footer();

    fprintf(stderr, "done!\n");

    return 0;
}

int main(int argc, char *argv[])
{
    if (argc < 2) {
        fprintf(stderr, "usage: %s REPOS_PATH [prefix]\n", argv[0]);
        return -1;
    }

    if (apr_initialize() != APR_SUCCESS) {
        fprintf(stderr, "You lose at apr_initialize().\n");
        return -1;
    }

    crawl_revisions(argv[1], (argc == 3 ? argv[2] : TRUNK));

    apr_terminate();

    return 0;
}
