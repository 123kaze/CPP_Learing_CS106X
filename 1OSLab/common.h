#ifndef COMMON_H
#define COMMON_H

#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <semaphore.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static inline void Die(const char *msg)
{
    perror(msg);
    exit(1);
}

static inline void ThreadDie(int rc, const char *msg)
{
    fprintf(stderr, "%s: %s\n", msg, strerror(rc));
    exit(1);
}



static inline double GetTime(void)
{
    struct timeval t;
    if (gettimeofday(&t, NULL) < 0) {
        Die("gettimeofday");
    }
    return (double)t.tv_sec + (double)t.tv_usec / 1000000.0;
}

static inline void Spin(double seconds)
{
    double start = GetTime();
    while (GetTime() - start < seconds) {
    }
}

static inline void *Malloc(size_t size)
{
    void *p = malloc(size);
    if (p == NULL) {
        Die("malloc");
    }
    return p;
}

static inline void *Calloc(size_t nmemb, size_t size)
{
    void *p = calloc(nmemb, size);
    if (p == NULL) {
        Die("calloc");
    }
    return p;
}

static inline void *Realloc(void *ptr, size_t size)
{
    void *p = realloc(ptr, size);
    if (p == NULL) {
        Die("realloc");
    }
    return p;
}

static inline char *Strdup(const char *s)
{
    size_t len = strlen(s) + 1;
    char *copy = Malloc(len);
    memcpy(copy, s, len);
    return copy;
}

static inline pid_t Fork(void)
{
    pid_t pid = fork();
    if (pid < 0) {
        Die("fork");
    }
    return pid;
}

static inline pid_t Wait(int *status)
{
    pid_t pid;
    do {
        pid = wait(status);
    } while (pid < 0 && errno == EINTR);

    if (pid < 0) {
        Die("wait");
    }
    return pid;
}

static inline pid_t Waitpid(pid_t pid, int *status, int options)
{
    pid_t rc;
    do {
        rc = waitpid(pid, status, options);
    } while (rc < 0 && errno == EINTR);

    if (rc < 0) {
        Die("waitpid");
    }
    return rc;
}

static inline int Open(const char *pathname, int flags, mode_t mode)
{
    int fd = open(pathname, flags, mode);
    if (fd < 0) {
        Die("open");
    }
    return fd;
}

static inline ssize_t Read(int fd, void *buf, size_t count)
{
    ssize_t n;
    do {
        n = read(fd, buf, count);
    } while (n < 0 && errno == EINTR);

    if (n < 0) {
        Die("read");
    }
    return n;
}

static inline ssize_t Write(int fd, const void *buf, size_t count)
{
    ssize_t n;
    do {
        n = write(fd, buf, count);
    } while (n < 0 && errno == EINTR);

    if (n < 0) {
        Die("write");
    }
    return n;
}

static inline void WriteAll(int fd, const void *buf, size_t count)
{
    const char *p = buf;
    while (count > 0) {
        ssize_t n = Write(fd, p, count);
        if (n == 0) {
            fprintf(stderr, "write: wrote 0 bytes\n");
            exit(1);
        }
        p += n;
        count -= (size_t)n;
    }
}

static inline void Close(int fd)
{
    if (close(fd) < 0) {
        Die("close");
    }
}

static inline void Pipe(int pipefd[2])
{
    if (pipe(pipefd) < 0) {
        Die("pipe");
    }
}

static inline void Dup2(int oldfd, int newfd)
{
    if (dup2(oldfd, newfd) < 0) {
        Die("dup2");
    }
}

static inline void Pthread_create(pthread_t *thread,
                                  const pthread_attr_t *attr,
                                  void *(*start_routine)(void *),
                                  void *arg)
{
    int rc = pthread_create(thread, attr, start_routine, arg);
    if (rc != 0) {
        ThreadDie(rc, "pthread_create");
    }
}

static inline void Pthread_join(pthread_t thread, void **retval)
{
    int rc = pthread_join(thread, retval);
    if (rc != 0) {
        ThreadDie(rc, "pthread_join");
    }
}

static inline void Pthread_detach(pthread_t thread)
{
    int rc = pthread_detach(thread);
    if (rc != 0) {
        ThreadDie(rc, "pthread_detach");
    }
}

static inline void Pthread_mutex_init(pthread_mutex_t *mutex,
                                      const pthread_mutexattr_t *attr)
{
    int rc = pthread_mutex_init(mutex, attr);
    if (rc != 0) {
        ThreadDie(rc, "pthread_mutex_init");
    }
}

static inline void Pthread_mutex_lock(pthread_mutex_t *mutex)
{
    int rc = pthread_mutex_lock(mutex);
    if (rc != 0) {
        ThreadDie(rc, "pthread_mutex_lock");
    }
}

static inline void Pthread_mutex_unlock(pthread_mutex_t *mutex)
{
    int rc = pthread_mutex_unlock(mutex);
    if (rc != 0) {
        ThreadDie(rc, "pthread_mutex_unlock");
    }
}

static inline void Pthread_mutex_destroy(pthread_mutex_t *mutex)
{
    int rc = pthread_mutex_destroy(mutex);
    if (rc != 0) {
        ThreadDie(rc, "pthread_mutex_destroy");
    }
}

static inline void Pthread_cond_init(pthread_cond_t *cond,
                                     const pthread_condattr_t *attr)
{
    int rc = pthread_cond_init(cond, attr);
    if (rc != 0) {
        ThreadDie(rc, "pthread_cond_init");
    }
}

static inline void Pthread_cond_wait(pthread_cond_t *cond,
                                     pthread_mutex_t *mutex)
{
    int rc = pthread_cond_wait(cond, mutex);
    if (rc != 0) {
        ThreadDie(rc, "pthread_cond_wait");
    }
}

static inline void Pthread_cond_signal(pthread_cond_t *cond)
{
    int rc = pthread_cond_signal(cond);
    if (rc != 0) {
        ThreadDie(rc, "pthread_cond_signal");
    }
}

static inline void Pthread_cond_broadcast(pthread_cond_t *cond)
{
    int rc = pthread_cond_broadcast(cond);
    if (rc != 0) {
        ThreadDie(rc, "pthread_cond_broadcast");
    }
}

static inline void Pthread_cond_destroy(pthread_cond_t *cond)
{
    int rc = pthread_cond_destroy(cond);
    if (rc != 0) {
        ThreadDie(rc, "pthread_cond_destroy");
    }
}

static inline void Sem_init(sem_t *sem, int pshared, unsigned int value)
{
    if (sem_init(sem, pshared, value) < 0) {
        Die("sem_init");
    }
}

static inline void Sem_wait(sem_t *sem)
{
    while (sem_wait(sem) < 0) {
        if (errno != EINTR) {
            Die("sem_wait");
        }
    }
}

static inline void Sem_post(sem_t *sem)
{
    if (sem_post(sem) < 0) {
        Die("sem_post");
    }
}

static inline void Sem_destroy(sem_t *sem)
{
    if (sem_destroy(sem) < 0) {
        Die("sem_destroy");
    }
}

#endif
